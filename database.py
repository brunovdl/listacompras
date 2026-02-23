import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

async def get_itens_lista():
    if not supabase: return []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").select("*").order("id", desc=True).execute()
        )
        return res.data
    except Exception as e:
        print(f"Erro ao buscar itens: {e}")
        return []

async def toggle_item_comprado(item_id: int, status: bool):
    if not supabase: return False
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").update({"comprado": status}).eq("id", item_id).execute()
        )
        return len(res.data) > 0
    except Exception as e:
        print(f"Erro ao atualizar item: {e}")
        return False

async def get_historico_compras():
    if not supabase: return []
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("historico_compras").select("*").order("data", desc=True).execute()
        )
        return res.data
    except Exception as e:
        print(f"Erro ao buscar histórico: {e}")
        return []

async def insert_itens_mock(itens: list):
    if not supabase: return False
    try:
        res = await asyncio.to_thread(
            lambda: supabase.table("itens_lista").insert(itens).execute()
        )
        return len(res.data) > 0
    except Exception as e:
        print(f"Erro ao inserir itens mock: {e}")
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

async def delete_itens_invalidos():
    """Remove itens com nomes inválidos gerados por parser quebrado (ex: 'Vl. Total...')."""
    if not supabase: return 0
    try:
        # Busca todos os itens
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
