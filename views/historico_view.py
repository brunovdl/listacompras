import flet as ft
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_historico_compras
from components.navbar import create_navbar

CARD_LIGHT = "#FFFFFF"
TEXT_DARK = "#0F172A"

def get_historico_view(page: ft.Page):
    # Header area
    filter_icon = ft.IconButton(icon=ft.Icons.FILTER_LIST, icon_color=TEXT_SECONDARY, icon_size=28)
    
    header_col = ft.Row([
        ft.Text("Histórico de Compras", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        filter_icon
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Total Card
    total_val_text = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    
    total_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_TODAY, color=TEXT_SECONDARY, size=14),
                ft.Text("TOTAL GASTO ESTE MÊS", color=TEXT_SECONDARY, size=11, weight=ft.FontWeight.BOLD)
            ], spacing=6),
            total_val_text,
            ft.Row([
                ft.Container(
                    content=ft.Text("+12%", size=10, weight=ft.FontWeight.BOLD, color="#10B981"),
                    bgcolor="rgba(16, 185, 129, 0.15)",
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4
                ),
                ft.Text("em relação ao mês passado", color=TEXT_SECONDARY, size=11)
            ], spacing=8)
        ], spacing=10),
        bgcolor=CARD_COLOR,
        border_radius=16,
        padding=24,
        margin=ft.margin.only(bottom=20)
    )

    # Atividades Recentes
    ativ_row = ft.Row([
        ft.Text("Atividades Recentes", size=16, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
        ft.Text("Ver tudo", size=13, weight=ft.FontWeight.W_500, color=CYAN)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    list_content = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True, spacing=15)

    main_container = ft.Container(
        content=ft.Column([
            header_col,
            ft.Container(height=10),
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
            nav_bar
        ],
        bgcolor=BG_COLOR,
        padding=0
    )

    def build_history_card(h):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.STOREFRONT, color=TEXT_PRIMARY, size=28),
                        bgcolor=BG_COLOR,
                        padding=14,
                        border_radius=12,
                        alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(h.get('mercado', 'Mercado'), color=TEXT_DARK, size=15, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{h.get('data', '12 Out, 2023')} • 18:30", color=TEXT_SECONDARY, size=12)
                    ], expand=True, spacing=2),
                    ft.Column([
                        ft.Text(f"R$ {h.get('total', 0):.2f}", color=TEXT_DARK, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("23 itens", color=TEXT_SECONDARY, size=12, text_align=ft.TextAlign.RIGHT)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    # Mock icons on bottom left
                    ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, color="#E2E8F0", size=16),
                        ft.Icon(ft.Icons.CIRCLE, color="#E2E8F0", size=16),
                        ft.Text("+20", color=TEXT_SECONDARY, size=11)
                    ], spacing=2),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.RECEIPT, color=CYAN, size=14),
                            ft.Text("Ver Cupom", color=CYAN, size=12, weight=ft.FontWeight.BOLD)
                        ], spacing=4),
                        bgcolor=BG_COLOR,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=8
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=15),
            bgcolor=CARD_LIGHT,
            border_radius=16,
            padding=20
        )

    async def perform_load_data(*args):
        historico = await get_historico_compras()
        
        list_content.controls.clear()
        
        if not historico:
            list_content.controls.append(ft.Container(
                content=ft.Text("Nenhum histórico encontrado!", color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center,
                padding=40
            ))
            view.update()
            return

        total_gasto = sum([h.get('total', 0) for h in historico])
        total_val_text.value = f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
        for h in historico:
            list_content.controls.append(build_history_card(h))
            
        list_content.controls.append(ft.Container(height=40))
        view.update()
        
    page.run_task(perform_load_data)
    return view
