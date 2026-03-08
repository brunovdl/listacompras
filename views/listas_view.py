import flet as ft
import asyncio
from datetime import date
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_listas, create_lista, delete_lista, get_itens_lista, registrar_compra_nfe
from components.navbar import create_navbar

def get_listas_view(page: ft.Page):

    list_content = ft.Column(spacing=12, expand=True)

    scroll_area = ft.Container(
        content=ft.Column([list_content], scroll=ft.ScrollMode.AUTO, expand=True),
        expand=True,
    )

    # ─── Banner de status do scanner QR ────────────────────────────────────────
    scan_progress = ft.ProgressBar(width=float('inf'), color=CYAN, bgcolor=CARD_COLOR, visible=False)
    scan_status_text = ft.Text("", size=12, color=TEXT_SECONDARY)
    scan_banner = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.QR_CODE_SCANNER, color=CYAN, size=16),
                scan_status_text
            ], spacing=6),
            scan_progress
        ], spacing=6),
        bgcolor=CARD_COLOR,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        visible=False,
        margin=ft.margin.only(bottom=8)
    )

    # ─── Scanner QR NF-e ────────────────────────────────────────────────────────
    async def qr_file_scan(file_path):
        scan_status_text.value = "Lendo QR Code da nota fiscal..."
        scan_progress.value = None
        scan_banner.visible = True
        scan_progress.visible = True
        view.update()
        try:
            from qrcode_service import get_items_from_nfe_qrcode
            nfe_items = await asyncio.to_thread(get_items_from_nfe_qrcode, file_path)
            if nfe_items and len(nfe_items) > 0:
                scan_status_text.value = f"Criando lista com {len(nfe_items)} itens..."
                view.update()
                lista = await registrar_compra_nfe(nfe_items)
                if lista:
                    scan_status_text.value = f"✅ Lista criada com {len(nfe_items)} itens!"
                    scan_progress.visible = False
                    scan_banner.visible = False
                    view.update()
                    page.go(f"/lista/{lista['id']}")
                else:
                    scan_status_text.value = "⚠️ Erro ao salvar no banco."
                    scan_progress.visible = False
                    view.update()
                    await asyncio.sleep(3)
                    scan_banner.visible = False
                    view.update()
            else:
                scan_status_text.value = "Nenhum item extraído da nota."
                scan_progress.visible = False
                view.update()
                await asyncio.sleep(2)
                scan_banner.visible = False
                view.update()
        except Exception as ex:
            print(f"Erro no QR Scanner: {ex}")
            scan_status_text.value = f"⚠️ {str(ex)[:70]}"
            scan_progress.visible = False
            view.update()
            await asyncio.sleep(4)
            scan_banner.visible = False
            view.update()

    def on_file_uploaded_qr(e: ft.FilePickerUploadEvent):
        if e.progress == 1.0:
            import os
            file_path = os.path.join("uploads", e.file_name)
            page.run_task(qr_file_scan, file_path)

    def on_file_picked_qr(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path:
                page.run_task(qr_file_scan, file_path)
            else:
                uf = []
                for f in e.files:
                    try:
                        uf.append(ft.FilePickerUploadFile(f.name, upload_url=page.get_upload_url(f.name, 60)))
                    except Exception as ex:
                        sb = ft.SnackBar(ft.Text(f"Erro no upload: {ex}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
                        page.overlay.append(sb)
                        page.update()
                        return
                file_picker_qr.upload(uf)

    file_picker_qr = ft.FilePicker(on_result=on_file_picked_qr, on_upload=on_file_uploaded_qr)

    async def abrir_lista(lista_id: int, e=None):
        page.go(f"/lista/{lista_id}")

    async def confirmar_exclusao_lista(lista_id: int, nome: str):
        async def fazer_exclusao(dlg):
            dlg.open = False
            page.update()
            ok = await delete_lista(lista_id)
            if ok:
                await perform_load_data()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Excluir lista?", color=TEXT_PRIMARY),
            content=ft.Text(f"Excluir \"{nome}\" e todos os seus itens?", color=TEXT_SECONDARY),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                ft.TextButton(
                    "Excluir",
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                    on_click=lambda e: page.run_task(fazer_exclusao, dlg),
                ),
            ],
            bgcolor=CARD_COLOR,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def build_lista_card(lista):
        lista_id = lista.get("id")
        nome = lista.get("nome", "Sem nome")
        descricao = lista.get("descricao", "")
        data_str = lista.get("data", "")

        # Formata data
        try:
            d = date.fromisoformat(data_str)
            data_fmt = d.strftime("%d/%m/%Y")
        except:
            data_fmt = data_str

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text(nome, size=15, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(descricao if descricao else "Sem descrição", size=11, color=TEXT_SECONDARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=11, color=TEXT_SECONDARY),
                            ft.Text(data_fmt, size=11, color=TEXT_SECONDARY),
                        ], spacing=4),
                    ], spacing=4, expand=True),
                    expand=True,
                    on_click=lambda e, lid=lista_id: page.run_task(abrir_lista, lid),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    icon_size=18,
                    tooltip="Excluir lista",
                    on_click=lambda e, lid=lista_id, n=nome: page.run_task(confirmar_exclusao_lista, lid, n),
                    style=ft.ButtonStyle(padding=ft.padding.all(4)),
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=CARD_COLOR,
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
        )

    async def perform_load_data():
        listas = await get_listas()
        list_content.controls.clear()

        if not listas:
            list_content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, color=TEXT_SECONDARY, size=50),
                        ft.Text("Nenhuma lista criada", color=TEXT_SECONDARY, size=14, text_align=ft.TextAlign.CENTER),
                        ft.Text("Toque em + para criar sua primeira lista", color=TEXT_SECONDARY, size=11, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.alignment.center,
                    padding=40,
                )
            )
        else:
            for lista in listas:
                list_content.controls.append(build_lista_card(lista))

        list_content.controls.append(ft.Container(height=80))
        view.update()

    # ─── Bottom Sheet para criar nova lista ───────────────────────────────────
    txt_nome_lista = ft.TextField(
        label="Nome da Lista",
        hint_text="Ex: Compras da Semana",
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        bgcolor=CARD_COLOR,
        border_radius=12,
        autofocus=True,
    )
    txt_desc_lista = ft.TextField(
        label="Descrição (opcional)",
        hint_text="Ex: Mercado do bairro",
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        bgcolor=CARD_COLOR,
        border_radius=12,
    )
    txt_data_lista = ft.TextField(
        label="Data",
        hint_text="DD/MM/AAAA",
        value=date.today().strftime("%d/%m/%Y"),
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        bgcolor=CARD_COLOR,
        border_radius=12,
        keyboard_type=ft.KeyboardType.DATETIME,
    )

    bs_error = ft.Text("", color=ft.Colors.RED_400, size=12)

    async def salvar_lista(e):
        nome = txt_nome_lista.value.strip()
        if not nome:
            bs_error.value = "Nome obrigatório!"
            page.update()
            return

        desc = txt_desc_lista.value.strip()
        data_val = txt_data_lista.value.strip()

        # Parseando a data no formato DD/MM/AAAA
        data_iso = str(date.today())
        try:
            partes = data_val.split("/")
            if len(partes) == 3:
                data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
        except:
            pass

        nova = await create_lista(nome, desc, data_iso)
        if nova:
            bs.open = False
            page.update()
            txt_nome_lista.value = ""
            txt_desc_lista.value = ""
            txt_data_lista.value = date.today().strftime("%d/%m/%Y")
            bs_error.value = ""
            await perform_load_data()
            # Abre diretamente a lista criada
            page.go(f"/lista/{nova['id']}")

    bs = ft.BottomSheet(
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Nova Lista", size=17, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=TEXT_SECONDARY, on_click=lambda e: setattr(bs, 'open', False) or page.update()),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=8),
                txt_nome_lista,
                ft.Container(height=8),
                txt_desc_lista,
                ft.Container(height=8),
                txt_data_lista,
                bs_error,
                ft.Container(height=12),
                ft.ElevatedButton(
                    content=ft.Text("Criar Lista", size=15, weight=ft.FontWeight.BOLD),
                    bgcolor=CYAN,
                    color=BG_COLOR,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                    height=50,
                    width=float('inf'),
                    on_click=lambda e: page.run_task(salvar_lista, e),
                ),
                ft.Container(height=16),
            ], tight=True),
            padding=ft.padding.only(left=20, right=20, top=20, bottom=40),
            bgcolor=CARD_COLOR,
        ),
        bgcolor=CARD_COLOR,
    )
    page.overlay.append(bs)

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=CYAN,
        foreground_color=BG_COLOR,
        on_click=lambda e: setattr(bs, 'open', True) or page.update(),
    )

    nav_bar = create_navbar(page, selected_index=0)

    header = ft.Column([
        ft.Row([
            ft.Text("Minhas Listas", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, color=CYAN, size=28),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Text("Selecione ou crie uma lista de compras", size=12, color=TEXT_SECONDARY),
        ft.Container(height=4),
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.QR_CODE_SCANNER, color=CYAN, size=18),
                ft.Text("Escanear Recibo / NF-e", color=CYAN, size=13, weight=ft.FontWeight.W_600)
            ], spacing=8),
            bgcolor=ft.Colors.with_opacity(0.08, CYAN),
            border=ft.border.all(1, CYAN),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            on_click=lambda _: file_picker_qr.pick_files(allow_multiple=False),
            ink=True,
        ),
    ], spacing=2)

    main_container = ft.Container(
        content=ft.Column([
            header,
            ft.Container(height=12),
            scan_banner,
            ft.Container(height=4),
            scroll_area,
        ], expand=True),
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=10),
        bgcolor=BG_COLOR,
    )

    view = ft.View(
        "/listas",
        [main_container, nav_bar, file_picker_qr],
        bgcolor=BG_COLOR,
        padding=0,
        floating_action_button=fab,
        floating_action_button_location=ft.FloatingActionButtonLocation.END_FLOAT,
    )

    async def load_data(*args):
        await perform_load_data()

    page.run_task(load_data)
    return view
