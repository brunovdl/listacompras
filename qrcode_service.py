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


def parse_nfe_items(html: str) -> list[dict]:
    """
    Extrai itens da página HTML da NF-e.
    Compatível com o layout padrão NFC-e (usado pela maioria dos estados).
    """
    soup = BeautifulSoup(html, "lxml")
    itens = []

    # ── Layout 1: tabela com classe 'table' (SP, MG, RS, PR, etc.) ──
    tabela = soup.find("table", {"id": "Prod"})
    if not tabela:
        tabela = soup.find("table", class_=re.compile(r"table", re.I))

    if tabela:
        linhas = tabela.find_all("tr")
        for linha in linhas[1:]:  # pular cabeçalho
            cols = linha.find_all("td")
            if len(cols) >= 3:
                nome = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                # Tenta encontrar a coluna de valor unitário ou vlr total
                preco_str = ""
                for col in reversed(cols):
                    txt = col.get_text(strip=True).replace(".", "").replace(",", ".")
                    if re.match(r"^\d+\.\d{2}$", txt):
                        preco_str = txt
                        break
                if nome:
                    try:
                        preco = float(preco_str) if preco_str else 0.0
                    except ValueError:
                        preco = 0.0
                    itens.append({
                        "nome": nome[:80],
                        "preco": preco,
                        "categoria": guess_categoria(nome),
                        "comprado": False
                    })
        if itens:
            return itens

    # ── Layout 2: divs com classe 'item' (alguns estados alternativos) ──
    divs_item = soup.find_all("span", class_=re.compile(r"Nome|txtTit|item", re.I))
    precos_div = soup.find_all("span", class_=re.compile(r"Vl|vlrItem|vTotLiq", re.I))

    for i, div_nome in enumerate(divs_item):
        nome = div_nome.get_text(strip=True)
        preco = 0.0
        if i < len(precos_div):
            try:
                preco = float(
                    precos_div[i].get_text(strip=True)
                    .replace(".", "").replace(",", ".")
                )
            except ValueError:
                pass
        if nome:
            itens.append({
                "nome": nome[:80],
                "preco": preco,
                "categoria": guess_categoria(nome),
                "comprado": False
            })

    return itens


def get_items_from_nfe_qrcode(image_path: str) -> list[dict]:
    """
    Pipeline completo:
    1. Decodifica QR Code da imagem
    2. Busca página SEFAZ
    3. Extrai e retorna lista de itens
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = decode_qrcode(image_path)
    if not url:
        raise ValueError("Nenhum QR Code válido de NF-e encontrado na imagem.")

    html = fetch_nfe_page(url)
    if not html:
        raise ValueError(f"Não foi possível acessar o portal SEFAZ.\nURL: {url}")

    itens = parse_nfe_items(html)
    if not itens:
        raise ValueError(
            "QR Code lido com sucesso, mas não foi possível extrair itens.\n"
            f"URL: {url}\n"
            "O estado pode ter um layout diferente."
        )

    print(f"[QR] {len(itens)} itens extraídos da NF-e.")
    return itens
