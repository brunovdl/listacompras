import re
import requests
import cv2
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

CATEGORIAS = {
    "frango": "Açougue", "carne": "Açougue", "picanha": "Açougue",
    "file": "Açougue", "filé": "Açougue", "linguiça": "Açougue",
    "queijo": "Frios", "presunto": "Frios", "mortadela": "Frios",
    "iogurte": "Frios", "cream": "Frios",
    "leite": "Mercado", "manteiga": "Mercado", "oleo": "Mercado",
    "óleo": "Mercado", "azeite": "Mercado", "arroz": "Mercado",
    "feijao": "Mercado", "feijão": "Mercado", "macarrao": "Mercado",
    "macarrão": "Mercado", "farinha": "Mercado", "açúcar": "Mercado",
    "acucar": "Mercado", "café": "Mercado", "cafe": "Mercado",
    "biscoito": "Mercado", "bolacha": "Mercado", "pao": "Mercado",
    "pão": "Mercado", "refrigerante": "Mercado", "suco": "Mercado",
    "sabao": "Limpeza", "sabão": "Limpeza", "detergente": "Limpeza",
    "desinfetante": "Limpeza", "amaciante": "Limpeza",
    "shampoo": "Limpeza", "condicionador": "Limpeza",
    "tomate": "Hortifruti", "alface": "Hortifruti", "banana": "Hortifruti",
    "maca": "Hortifruti", "maçã": "Hortifruti", "laranja": "Hortifruti",
    "limao": "Hortifruti", "limão": "Hortifruti", "cenoura": "Hortifruti",
    "batata": "Hortifruti", "cebola": "Hortifruti", "alho": "Hortifruti",
}


def guess_categoria(nome: str) -> str:
    nome_lower = nome.lower()
    for kw, cat in CATEGORIAS.items():
        if kw in nome_lower:
            return cat
    return "Mercado"


def _decode_with_opencv(image_path: str) -> str | None:
    """Decodifica QR Code usando OpenCV (sem DLL externas)."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            # Tenta via PIL → numpy (para imagens com paths especiais)
            pil_img = Image.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if data and data.startswith("http"):
            print(f"[QR/cv2] URL: {data}")
            return data

        # Tenta com preprocessing (melhora leitura de QRs difíceis)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        data, _, _ = detector.detectAndDecode(thresh)
        if data and data.startswith("http"):
            print(f"[QR/cv2+thresh] URL: {data}")
            return data

        return None
    except Exception as e:
        print(f"[QR/cv2] Erro: {e}")
        return None


def _decode_with_pyzbar(image_path: str) -> str | None:
    """Fallback: decodifica via pyzbar (requer libzbar DLL no Windows)."""
    try:
        from pyzbar.pyzbar import decode as qr_decode
        img = Image.open(image_path)
        decoded = qr_decode(img)
        for obj in decoded:
            data = obj.data.decode("utf-8").strip()
            if data.startswith("http"):
                print(f"[QR/pyzbar] URL: {data}")
                return data
        return None
    except Exception as e:
        print(f"[QR/pyzbar] Erro (ignorado): {e}")
        return None


def decode_qrcode(image_path: str) -> str | None:
    """Tenta OpenCV primeiro; fallback para pyzbar se disponível."""
    url = _decode_with_opencv(image_path)
    if url:
        return url
    url = _decode_with_pyzbar(image_path)
    if url:
        return url
    print("[QR] Nenhum QR Code válido de NF-e encontrado.")
    return None



def fetch_nfe_page(url: str) -> str | None:
    """Busca o HTML da página de consulta de NF-e no SEFAZ."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        resp.encoding = "utf-8"
        if resp.status_code == 200:
            return resp.text
        print(f"[QR] SEFAZ retornou status {resp.status_code}")
        return None
    except Exception as e:
        print(f"[QR] Erro ao buscar página SEFAZ: {e}")
        return None


def _to_float(txt: str) -> float:
    """
    Extrai e converte o último valor monetário de uma string.
    Suporta: 'Vl. Total3,19', '1.234,56', 'R$ 12,50', '3,19', '39.90'.
    """
    # Tenta extrair padrão com vírgula decimal (BRL): ex '3,19' ou '1.234,56'
    matches = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", txt)
    if matches:
        raw = matches[-1].replace(".", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass

    # Tenta padrão com ponto decimal: ex '3.19' ou '39.90'
    matches = re.findall(r"\d+\.\d{2}", txt)
    if matches:
        try:
            return float(matches[-1])
        except ValueError:
            pass

    return 0.0


def parse_nfe_items(html: str) -> list[dict]:
    """
    Extrai itens + preços da página HTML da NF-e.
    Tenta múltiplos layouts utilizados pelos estados brasileiros.
    """
    soup = BeautifulSoup(html, "lxml")
    itens = []

    # ── DEBUG: salva o HTML para inspeção se não encontrar preços ──
    print("[QR] Iniciando parse do HTML da NF-e...")

    # ── Estratégia A: Layout NFC-e padrão (SP, MG, RS, PR, GO, etc.) ──
    # Estrutura: <table id="tabResult"> ou tabelas com colunas bem definidas
    # Cabeçalho típico: Código | Descrição | Qtd | Un | Vl Unit | Vl Total
    tabelas = soup.find_all("table")
    print(f"[QR] Tabelas encontradas: {len(tabelas)}")

    for tabela in tabelas:
        linhas = tabela.find_all("tr")
        if len(linhas) < 2:
            continue

        # Detecta colunas pelo cabeçalho
        header = linhas[0]
        header_texts = [th.get_text(strip=True).lower() for th in header.find_all(["th", "td"])]
        print(f"[QR] Cabeçalho tabela: {header_texts}")

        # Identifica índices das colunas por nome
        idx_nome = idx_preco = -1
        for i, h in enumerate(header_texts):
            if any(k in h for k in ["descrição", "descricao", "produto", "item", "nome"]):
                idx_nome = i
            if any(k in h for k in ["vl total", "valor total", "vltotal", "total", "vl. total"]):
                idx_preco = i

        # Se não encontrou pelo cabeçalho, default: col 0 = nome, última = total
        if idx_nome == -1:
            idx_nome = 0
        if idx_preco == -1:
            idx_preco = -1  # última coluna

        print(f"[QR] idx_nome={idx_nome}, idx_preco={idx_preco}")

        temp_itens = []
        for linha in linhas[1:]:
            cols = linha.find_all("td")
            if len(cols) < 2:
                continue

            # Quando só há 2 colunas: col[0]=bloco do produto, col[1]="Vl. TotalX,XX"
            # Independente do que o cabeçalho indicou, forçamos idx=0
            nome_idx = 0 if len(cols) == 2 else idx_nome

            # col[0] pode conter: "AGUA MIN LEVITY 1,5L(Código:12345)Qtde.:1 UN:UN Vl. Unit.:3,19"
            # Pegamos somente a primeira parte (nome real do produto)
            bloco = cols[nome_idx].get_text(separator="\n", strip=True) if nome_idx < len(cols) else ""
            # Corta no primeiro separador de info extra
            for sep in ["(Código", "(Cod", "Código", "Qtde", "Vl. Unit", "\n", "\r"]:
                if sep in bloco:
                    bloco = bloco.split(sep)[0]
            nome = bloco.strip()

            if not nome or len(nome) < 2:
                continue

            # Extrai preço de todas as colunas exceto a do nome (usando índice)
            preco = 0.0
            for i, col in enumerate(cols):
                if i == nome_idx:
                    continue
                raw = col.get_text(strip=True)
                print(f"[QR] col[{i}] raw = '{raw}'  → _to_float = {_to_float(raw)}")
                val = _to_float(raw)
                if val > 0:
                    preco = val
                    break

            print(f"[QR] ✅ '{nome}' → R$ {preco:.2f}")
            temp_itens.append({
                "nome": nome[:60],
                "preco": preco,
                "categoria": guess_categoria(nome),
                "comprado": False
            })

        if temp_itens:
            itens.extend(temp_itens)
            break  # Usa a primeira tabela que retornar itens válidos

    if itens:
        return itens

    # ── Estratégia B: Spans e divs (NFC-e de alguns estados como BA, CE) ──
    # Nome em span.txtTit / txtNome, valor em span.valor / vlrItem
    nomes_span = soup.find_all("span", class_=re.compile(r"txtTit|txtNome|Nome|item", re.I))
    valores_span = soup.find_all("span", class_=re.compile(r"valor|vlrItem|vTotLiq|Vl|price", re.I))

    print(f"[QR] Estratégia B: {len(nomes_span)} nomes, {len(valores_span)} valores")

    for i, span_nome in enumerate(nomes_span):
        nome = span_nome.get_text(strip=True)
        preco = 0.0

        # Tenta pegar valor no mesmo container pai
        pai = span_nome.find_parent()
        if pai:
            todos_textos = pai.find_all(string=re.compile(r"\d+[.,]\d{2}"))
            for t in reversed(todos_textos):
                val = _to_float(str(t))
                if val > 0:
                    preco = val
                    break

        # Fallback: usa lista de spans de valor na mesma posição
        if preco == 0.0 and i < len(valores_span):
            preco = _to_float(valores_span[i].get_text(strip=True))

        if nome:
            print(f"[QR B] Item: '{nome}' | Preço: {preco}")
            itens.append({
                "nome": nome[:80],
                "preco": preco,
                "categoria": guess_categoria(nome),
                "comprado": False
            })

    return itens



def parse_nfe_items_with_groq(html: str) -> list[dict]:
    """
    Usa o Groq (modelo openai/gpt-oss-20b) para extrair itens do HTML da NF-e.
    Retorna lista de dicts com nome, categoria, preco e comprado.
    """
    import os
    import json
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY não configurada no .env")

    # Extrai somente o texto visível da página, ignorando scripts/styles
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "nav", "footer", "noscript"]):
        tag.decompose()
    texto_puro = soup.get_text(separator="\n", strip=True)

    # Limita o texto a ~8000 chars para não estourar o contexto
    texto_puro = texto_puro[:8000]

    print(f"[QR/Groq] Texto extraído do SEFAZ ({len(texto_puro)} chars). Enviando ao Groq...")

    prompt = (
        "Você é um assistente especializado em notas fiscais brasileiras (NF-e/NFC-e). "
        "Abaixo está o texto extraído de uma página de consulta de nota fiscal no portal SEFAZ. "
        "Extraia APENAS os itens de produto que foram comprados (ignore totais, taxas, descontos, "
        "informações do estabelecimento, dados do consumidor, forma de pagamento e rodapé). "
        "Para cada produto retorne EXATAMENTE um JSON com as chaves:\n"
        "  nome (string, nome do produto),\n"
        "  categoria (escolha entre: Mercado, Hortifruti, Açougue, Frios, Limpeza, Padaria, Outros),\n"
        "  preco (float, valor total do item — não unitário).\n\n"
        "Retorne SOMENTE um JSON Array. Sem markdown, sem texto extra, sem chave raiz.\n\n"
        f"TEXTO DA NOTA:\n{texto_puro}"
    )

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-oss-20b",
        temperature=0.1,
    )

    raw = resp.choices[0].message.content or ""
    print(f"[QR/Groq] Resposta bruta: {raw[:300]}")

    # Remove possível markdown
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "itens" in data:
            data = data["itens"]
        if not isinstance(data, list):
            raise ValueError("Resposta do Groq não é uma lista")
    except Exception as e:
        print(f"[QR/Groq] Erro ao parsear JSON: {e}")
        return []

    itens = []
    for item in data:
        nome = str(item.get("nome", "")).strip()
        categoria = str(item.get("categoria", "Mercado")).strip()
        try:
            preco = float(item.get("preco", 0.0))
        except (ValueError, TypeError):
            preco = 0.0
        if nome and len(nome) > 1:
            itens.append({
                "nome": nome[:80],
                "preco": preco,
                "categoria": categoria,
                "comprado": False
            })

    print(f"[QR/Groq] {len(itens)} itens extraídos pela IA.")
    return itens


def get_items_from_nfe_qrcode(image_path: str) -> list[dict]:
    """
    Pipeline completo:
    1. Decodifica QR Code da imagem
    2. Busca página SEFAZ
    3. Envia HTML ao Groq (openai/gpt-oss-20b) para extrair nome, categoria e preço
    4. Retorna lista de itens para inserção no banco
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = decode_qrcode(image_path)
    if not url:
        raise ValueError("Nenhum QR Code válido de NF-e encontrado na imagem.")

    html = fetch_nfe_page(url)
    if not html:
        raise ValueError(f"Não foi possível acessar o portal SEFAZ.\nURL: {url}")

    # Tenta parser via Groq primeiro
    try:
        itens = parse_nfe_items_with_groq(html)
    except Exception as e:
        print(f"[QR] Groq falhou ({e}), tentando parser HTML clássico...")
        itens = []

    # Fallback para parser HTML se Groq falhar ou retornar vazio
    if not itens:
        print("[QR] Usando parser HTML como fallback...")
        itens = parse_nfe_items(html)

    if not itens:
        raise ValueError(
            "QR Code lido com sucesso, mas não foi possível extrair itens.\n"
            f"URL: {url}\n"
            "Verifique se a chave GROQ_API_KEY está configurada corretamente."
        )

    print(f"[QR] {len(itens)} itens prontos para inserção no banco.")
    return itens
