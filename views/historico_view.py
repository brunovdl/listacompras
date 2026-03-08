import flet as ft
import asyncio
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_historico_compras, registrar_compra_nfe
from components.navbar import create_navbar

CARD_LIGHT = "#FFFFFF"
TEXT_DARK = "#0F172A"

def get_historico_view(page: ft.Page):

    # ─── Banner de status do scanner QR ──────────────────────────────────────
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
        margin=ft.margin.only(bottom=10)
    )

    # ─── Scanner QR NF-e ─────────────────────────────────────────────────────
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
                scan_status_text.value = f"Registrando {len(nfe_items)} itens..."
                view.update()
                lista = await registrar_compra_nfe(nfe_items)
                if lista:
                    scan_status_text.value = f"✅ {len(nfe_items)} itens adicionados ao histórico!"
                    scan_progress.visible = False
                    view.update()
                    await asyncio.sleep(1.5)
                    await perform_load_data()
                else:
                    scan_status_text.value = "⚠️ Erro ao salvar no banco."
                    scan_progress.visible = False
                    view.update()
                    await asyncio.sleep(3)
            else:
                scan_status_text.value = "Nenhum item extraído da nota."
                scan_progress.visible = False
                view.update()
                await asyncio.sleep(2)
        except Exception as ex:
            print(f"Erro no QR Scanner: {ex}")
            scan_status_text.value = f"⚠️ {str(ex)[:60]}"
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

    # ─── Header ──────────────────────────────────────────────────────────────
    header_col = ft.Row([
        ft.Text("Histórico de Compras", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.QR_CODE_SCANNER, color=BG_COLOR, size=18),
                ft.Text("Importar NF-e", color=BG_COLOR, size=12, weight=ft.FontWeight.W_600)
            ], spacing=6),
            bgcolor=CYAN,
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            on_click=lambda _: file_picker_qr.pick_files(allow_multiple=False),
            ink=True,
        )
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ─── Card de total do mês ─────────────────────────────────────────────────
    total_val_text = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)

    total_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, color=TEXT_SECONDARY, size=14),
                ft.Text("TOTAL GASTO (HISTÓRICO COMPLETO)", color=TEXT_SECONDARY, size=11, weight=ft.FontWeight.BOLD)
            ], spacing=6),
            total_val_text,
            ft.Row([
                ft.Icon(ft.Icons.QR_CODE_2, color=TEXT_SECONDARY, size=12),
                ft.Text("Importado via QR Code NF-e", color=TEXT_SECONDARY, size=11)
            ], spacing=6)
        ], spacing=10),
        bgcolor=CARD_COLOR,
        border_radius=16,
        padding=24,
        margin=ft.margin.only(bottom=16)
    )

    # ─── Atividades Recentes ──────────────────────────────────────────────────
    ativ_row = ft.Row([
        ft.Text("Atividades Recentes", size=16, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    list_content = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True, spacing=15)

    main_container = ft.Container(
        content=ft.Column([
            header_col,
            ft.Container(height=10),
            scan_banner,
            total_card,
            ativ_row,
            ft.Container(height=5),
            list_content,
        ], expand=True),
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=0),
        bgcolor=BG_COLOR
    )

    nav_bar = create_navbar(page, 1)

    view = ft.View(
        "/historico",
        [
            main_container,
            nav_bar,
            file_picker_qr,
        ],
        bgcolor=BG_COLOR,
        padding=0
    )

    def build_history_card(h):
        nome = h.get('mercado', 'Compra')
        data_str = h.get('data', '')
        total_val = h.get('total', 0)
        qtd = h.get('qtd_itens', 0)
        is_nfe = "nf-e" in (h.get('descricao') or '').lower() or "nf" in nome.lower()

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.QR_CODE_2 if is_nfe else ft.Icons.STOREFRONT,
                            color=TEXT_PRIMARY, size=28
                        ),
                        bgcolor=BG_COLOR,
                        padding=14,
                        border_radius=12,
                        alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(nome, color=TEXT_DARK, size=15, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=11, color=TEXT_SECONDARY),
                            ft.Text(data_str, color=TEXT_SECONDARY, size=12)
                        ], spacing=4),
                    ], expand=True, spacing=2),
                    ft.Column([
                        ft.Text(
                            f"R$ {total_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            color=TEXT_DARK, size=18, weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(f"{qtd} itens", color=TEXT_SECONDARY, size=12, text_align=ft.TextAlign.RIGHT)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Container(
                        content=ft.Text(
                            "NF-e" if is_nfe else "Lista",
                            size=10, weight=ft.FontWeight.BOLD,
                            color=CYAN if is_nfe else TEXT_SECONDARY
                        ),
                        bgcolor=ft.Colors.with_opacity(0.1, CYAN) if is_nfe else BG_COLOR,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        border_radius=6,
                        border=ft.border.all(1, CYAN if is_nfe else TEXT_SECONDARY)
                    ),
                    ft.Text(
                        h.get('descricao', '') or '',
                        color=TEXT_SECONDARY, size=11
                    ),
                ], spacing=8)
            ], spacing=12),
            bgcolor=CARD_LIGHT,
            border_radius=16,
            padding=20
        )

    async def perform_load_data(*args):
        historico = await get_historico_compras()

        total_gasto = sum([h.get('total', 0) for h in historico])
        total_val_text.value = f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        list_content.controls.clear()

        if not historico:
            list_content.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, color=TEXT_SECONDARY, size=50),
                    ft.Text("Nenhuma compra registrada", color=TEXT_SECONDARY, size=14, text_align=ft.TextAlign.CENTER),
                    ft.Text("Use o botão 'Importar NF-e' para registrar uma compra", color=TEXT_SECONDARY, size=11, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                alignment=ft.alignment.center,
                padding=40
            ))
            view.update()
            return

        for h in historico:
            list_content.controls.append(build_history_card(h))

        list_content.controls.append(ft.Container(height=40))
        view.update()

    page.run_task(perform_load_data)
    return view
