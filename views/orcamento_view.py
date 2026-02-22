import flet as ft
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_historico_compras
from components.navbar import create_navbar

def get_orcamento_view(page: ft.Page):
    # Header area
    btn_analise = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.AUTO_AWESOME, color=CYAN, size=14),
            ft.Text("Análise IA", color=CYAN, size=12, weight=ft.FontWeight.W_600)
        ], spacing=4),
        bgcolor=CARD_COLOR,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=16
    )
    
    header_col = ft.Row([
        ft.Text("Orçamento", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        btn_analise
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Variables for goal calculation (Mocked goal)
    meta_global = 2000.00
    
    # This will be updated on data load
    progress_container = ft.Container(
        content=ft.Stack([
            ft.ProgressRing(width=200, height=200, stroke_width=12, color=CYAN, bgcolor=CARD_COLOR, value=0.0)
        ], alignment=ft.alignment.center),
        alignment=ft.alignment.center,
        margin=ft.margin.only(top=30, bottom=20)
    )

    list_content = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True, spacing=15)

    cat_row = ft.Row([
        ft.Text("Categorias", size=16, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
        ft.Text("Ver tudo", size=13, weight=ft.FontWeight.W_500, color=CYAN)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    main_container = ft.Container(
        content=ft.Column([
            header_col,
            progress_container,
            ft.Text(f"Meta definida: R$ {meta_global:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
                    color=TEXT_SECONDARY, size=12, text_align=ft.TextAlign.CENTER),
            ft.Container(height=20),
            cat_row,
            ft.Container(height=5),
            list_content,
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=0),
        bgcolor=BG_COLOR
    )

    nav_bar = create_navbar(page, 2)

    view = ft.View(
        "/orcamento",
        [
            main_container,
            nav_bar
        ],
        bgcolor=BG_COLOR,
        padding=0
    )

    def build_category_row(nome, icon_name, gasto, meta):
        pct = gasto / meta if meta > 0 else 0
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon_name, color=TEXT_PRIMARY, size=28),
                        bgcolor=CARD_COLOR,
                        padding=14,
                        border_radius=12,
                        alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(nome, color=TEXT_PRIMARY, size=15, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{int(pct*100)}%", color=TEXT_SECONDARY, size=11)
                    ], expand=True, spacing=2),
                    ft.Column([
                        ft.Text(f"R$ {gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=TEXT_PRIMARY, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Meta: R$ {meta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=TEXT_SECONDARY, size=11, text_align=ft.TextAlign.RIGHT)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=ft.ProgressBar(value=pct, color=CYAN, bgcolor=CARD_COLOR, height=6),
                    border_radius=4,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE
                )
            ], spacing=10),
            bgcolor=BG_COLOR,
            margin=ft.margin.only(bottom=10)
        )

    async def perform_load_data(*args):
        historico = await get_historico_compras()
        
        total_gasto = sum([h.get('total', 0) for h in historico])
        pct_global = total_gasto / meta_global if meta_global > 0 else 0
        
        # Center of Progress Ring
        center_content = ft.Column([
            ft.Text("Gasto Mensal", color=TEXT_SECONDARY, size=12),
            ft.Text(f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), color=TEXT_PRIMARY, size=24, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text(f"{int(pct_global*100)}% da Meta", size=10, weight=ft.FontWeight.BOLD, color=BG_COLOR),
                bgcolor=CYAN,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                border_radius=10
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

        # Update Progress Ring
        progress_container.content = ft.Stack([
            ft.ProgressRing(width=200, height=200, stroke_width=12, color=CYAN, bgcolor=CARD_COLOR, value=pct_global),
            ft.Container(content=center_content, alignment=ft.alignment.center, width=200, height=200)
        ], alignment=ft.alignment.center)
        
        list_content.controls.clear()
        
        # Mocks categories based on total (if any), otherwise show empty or default mocks
        if total_gasto == 0:
            list_content.controls.append(ft.Text("Nenhum dado categorizado.", color=TEXT_SECONDARY))
        else:
            list_content.controls.append(build_category_row("Mercado", ft.Icons.SHOPPING_CART, total_gasto * 0.6, 1300.00))
            list_content.controls.append(build_category_row("Limpeza", ft.Icons.CLEANING_SERVICES, total_gasto * 0.3, 500.00))
            list_content.controls.append(build_category_row("Hortifruti", ft.Icons.APPLE, total_gasto * 0.1, 200.00))
            
        list_content.controls.append(ft.Container(height=40))
        view.update()
        
    page.run_task(perform_load_data)
    return view
