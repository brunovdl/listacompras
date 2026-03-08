import os
import asyncio
from datetime import date
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# ─────────────────────────────────────────────────
# LISTAS
# ─────────────────────────────────────────────────

async def get_listas():
    """Retorna todas as listas ordenadas pela data mais recente."""
    if not supabase: return []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("listas").select("*").order("data", desc=True).execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Erro ao buscar listas: {e}")
        return []

async def create_lista(nome: str, descricao: str = "", data_lista: str = None):
    """Cria uma nova lista de compras."""
    if not supabase: return None
    try:
        payload = {
            "nome": nome,
            "descricao": descricao,
            "data": data_lista or str(date.today()),
        }
        res = await asyncio.to_thread(
            lambda: supabase.table("listas").insert(payload).execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao criar lista: {e}")
        return None

async def update_lista(lista_id: int, dados: dict):
    """Atualiza nome/descrição/data de uma lista."""
    if not supabase: return False
    try:
        await asyncio.to_thread(
            lambda: supabase.table("listas").update(dados).eq("id", lista_id).execute()
        )
        return True
    except Exception as e:
        print(f"Erro ao atualizar lista: {e}")
        return False

async def delete_lista(lista_id: int):
    """Remove a lista e todos os seus itens (CASCADE)."""
    if not supabase: return False
    try:
        await asyncio.to_thread(
            lambda: supabase.table("listas").delete().eq("id", lista_id).execute()
        )
        return True
    except Exception as e:
        print(f"Erro ao excluir lista: {e}")
        return False

async def get_lista_by_id(lista_id: int):
    """Retorna os dados de uma lista específica."""
    if not supabase: return None
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("listas").select("*").eq("id", lista_id).single().execute()
        )
        return res.data
    except Exception as e:
        print(f"Erro ao buscar lista {lista_id}: {e}")
        return None

# ─────────────────────────────────────────────────
# ITENS
# ─────────────────────────────────────────────────

async def get_itens_lista(lista_id: int):
    """Retorna itens de uma lista específica."""
    if not supabase: return []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista")
                .select("*")
                .eq("lista_id", lista_id)
                .order("id", desc=True)
                .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Erro ao buscar itens: {e}")
        return []

async def toggle_item_comprado(item_id: int, status: bool):
    if not supabase: return False
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").update({"comprado": not status}).eq("id", item_id).execute()
        )
        return len(res.data) > 0
    except Exception as e:
        print(f"Erro ao atualizar item: {e}")
        return False

async def insert_item(dados: dict):
    if not supabase: return False
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").insert(dados).execute()
        )
        return len(res.data) > 0
    except Exception as e:
        print(f"Erro ao inserir item: {e}")
        return False

async def delete_item(item_id: int):
    if not supabase: return False
    try:
        await asyncio.to_thread(
            lambda: supabase.table("itens_lista").delete().eq("id", item_id).execute()
        )
        return True
    except Exception as e:
        print(f"Erro ao excluir item: {e}")
        return False

async def update_item(item_id: int, dados: dict):
    if not supabase: return False
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").update(dados).eq("id", item_id).execute()
        )
        return len(res.data) > 0
    except Exception as e:
        print(f"Erro ao atualizar item: {e}")
        return False


# ─────────────────────────────────────────────────
# NF-e — REGISTRAR COMPRA FINALIZADA
# ─────────────────────────────────────────────────

async def registrar_compra_nfe(itens: list, mercado: str = "Compra NF-e", data_compra: str = None):
    """
    Cria uma lista automática com os itens da NF-e, todos marcados como comprado=True.
    Retorna a lista criada ou None em caso de erro.
    """
    if not supabase:
        return None
    from datetime import date as _date
    data_str = data_compra or str(_date.today())
    nome_lista = f"{mercado} — {data_str}"
    lista = await create_lista(nome_lista, "Importado via QR NF-e", data_str)
    if not lista:
        return None
    lista_id = lista["id"]
    for item in itens:
        item["lista_id"] = lista_id
        item["comprado"] = True  # já comprado — vai direto ao histórico
        await insert_item(item)
    return lista


# ─────────────────────────────────────────────────
# HISTÓRICO
# ─────────────────────────────────────────────────

async def get_historico_compras():
    """Retorna o histórico de compras (listas) com o total gasto em cada uma."""
    if not supabase:
        return []
    try:
        res_listas = await asyncio.to_thread(
            lambda: supabase.table("listas").select("*").order("data", desc=True).execute()
        )
        listas = res_listas.data or []

        historico = []
        for lista in listas:
            lista_id = lista.get("id")
            res_itens = await asyncio.to_thread(
                lambda lid=lista_id: supabase.table("itens_lista")
                    .select("preco, nome")
                    .eq("lista_id", lid)
                    .execute()
            )
            itens = res_itens.data or []

            total = sum(float(item.get("preco") or 0) for item in itens)

            historico.append({
                "id": lista_id,
                "mercado": lista.get("nome", "Mercado"),
                "descricao": lista.get("descricao", ""),
                "data": lista.get("data", ""),
                "total": total,
                "qtd_itens": len(itens),
            })

        return historico
    except Exception as e:
        print(f"Erro ao buscar histórico de compras: {e}")
        return []


async def get_totais_por_categoria():
    """
    Retorna o total gasto agrupado por categoria, considerando todos os itens
    marcados como comprado=True (já comprados via NF-e ou marcados na lista).
    Retorna: list[dict] com {categoria, total, qtd_itens}
    """
    if not supabase:
        return []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista")
                .select("preco, categoria, comprado")
                .eq("comprado", True)
                .execute()
        )
        itens = res.data or []

        totais: dict[str, dict] = {}
        for item in itens:
            cat = item.get("categoria") or "Outros"
            preco = float(item.get("preco") or 0)
            if cat not in totais:
                totais[cat] = {"total": 0.0, "qtd_itens": 0}
            totais[cat]["total"] += preco
            totais[cat]["qtd_itens"] += 1

        return [
            {"categoria": cat, "total": v["total"], "qtd_itens": v["qtd_itens"]}
            for cat, v in sorted(totais.items(), key=lambda x: -x[1]["total"])
        ]
    except Exception as e:
        print(f"Erro ao buscar totais por categoria: {e}")
        return []


async def delete_itens_invalidos():

    """Remove itens com nomes inválidos gerados por parser quebrado."""
    if not supabase: return 0
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").select("id, nome").execute()
        )
        itens = res.data or []
        PREFIXOS_INVALIDOS = ("vl. total", "vl.total", "total", "subtotal")
        ids_invalidos = [
            item["id"] for item in itens
            if item.get("nome", "").lower().strip().startswith(PREFIXOS_INVALIDOS)
        ]
        if ids_invalidos:
            for item_id in ids_invalidos:
                await asyncio.to_thread(
                    lambda iid=item_id: supabase.table("itens_lista").delete().eq("id", iid).execute()
                )
            print(f"[DB] {len(ids_invalidos)} itens inválidos removidos.")
        return len(ids_invalidos)
    except Exception as e:
        print(f"Erro ao limpar itens inválidos: {e}")
        return 0
