import flet as ft
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_historico_compras, get_totais_por_categoria
from components.navbar import create_navbar

# Ícones por categoria
ICONES_CATEGORIA = {
    "Mercado":    ft.Icons.SHOPPING_BASKET,
    "Hortifruti": ft.Icons.APPLE,
    "Açougue":    ft.Icons.SET_MEAL,
    "Frios":      ft.Icons.KITCHEN,
    "Limpeza":    ft.Icons.CLEANING_SERVICES,
    "Padaria":    ft.Icons.BAKERY_DINING,
    "Outros":     ft.Icons.CATEGORY_OUTLINED,
}

def get_orcamento_view(page: ft.Page):

    header_col = ft.Row([
        ft.Text("Orçamento", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=TEXT_SECONDARY, size=14),
                ft.Text("Itens comprados", color=TEXT_SECONDARY, size=11)
            ], spacing=4),
            bgcolor=CARD_COLOR,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=16
        )
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ─── Anel de progresso ────────────────────────────────────────────────────
    progress_container = ft.Container(
        content=ft.Stack([
            ft.ProgressRing(width=200, height=200, stroke_width=12, color=CYAN, bgcolor=CARD_COLOR, value=0.0)
        ], alignment=ft.alignment.center),
        alignment=ft.alignment.center,
        margin=ft.margin.only(top=20, bottom=10)
    )
    meta_text = ft.Text("Meta: R$ 2.000,00", color=TEXT_SECONDARY, size=12, text_align=ft.TextAlign.CENTER)

    # ─── Resumo compacto ─────────────────────────────────────────────────────
    resumo_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER, spacing=16)

    # ─── Lista de categorias ─────────────────────────────────────────────────
    cat_header = ft.Row([
        ft.Text("Gastos por Categoria", size=16, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
    ])
    list_content = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True, spacing=10)

    main_container = ft.Container(
        content=ft.Column([
            header_col,
            progress_container,
            meta_text,
            ft.Container(height=6),
            resumo_row,
            ft.Container(height=16),
            cat_header,
            ft.Container(height=4),
            list_content,
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=0),
        bgcolor=BG_COLOR
    )

    nav_bar = create_navbar(page, 2)

    view = ft.View(
        "/orcamento",
        [main_container, nav_bar],
        bgcolor=BG_COLOR,
        padding=0
    )

    def fmt(valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def build_category_row(cat: str, gasto: float, total_geral: float, qtd: int):
        pct = gasto / total_geral if total_geral > 0 else 0
        icon = ICONES_CATEGORIA.get(cat, ft.Icons.CATEGORY_OUTLINED)
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color=TEXT_PRIMARY, size=22),
                        bgcolor=CARD_COLOR,
                        padding=10,
                        border_radius=10,
                        alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(cat, color=TEXT_PRIMARY, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{qtd} item(ns) • {int(pct*100)}% do total", color=TEXT_SECONDARY, size=11)
                    ], expand=True, spacing=2),
                    ft.Text(fmt(gasto), color=TEXT_PRIMARY, size=14, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(
                    content=ft.ProgressBar(value=pct, color=CYAN, bgcolor=CARD_COLOR, height=5),
                    border_radius=4,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE
                )
            ], spacing=8),
            bgcolor=BG_COLOR,
            margin=ft.margin.only(bottom=4)
        )

    META_GLOBAL = 2000.00

    async def perform_load_data(*args):
        # Busca dados reais
        historico = await get_historico_compras()
        categorias = await get_totais_por_categoria()

        total_gasto = sum(h.get("total", 0) for h in historico)
        total_comprado = sum(c.get("total", 0) for c in categorias)
        qtd_compras = len(historico)
        pct_global = total_gasto / META_GLOBAL if META_GLOBAL > 0 else 0

        # Anel de progresso
        center_content = ft.Column([
            ft.Text("Total Gasto", color=TEXT_SECONDARY, size=12),
            ft.Text(fmt(total_gasto), color=TEXT_PRIMARY, size=22, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Text(f"{int(pct_global * 100)}% da Meta", size=10, weight=ft.FontWeight.BOLD, color=BG_COLOR),
                bgcolor=CYAN,
                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                border_radius=10
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

        progress_container.content = ft.Stack([
            ft.ProgressRing(width=200, height=200, stroke_width=12, color=CYAN, bgcolor=CARD_COLOR, value=min(pct_global, 1.0)),
            ft.Container(content=center_content, alignment=ft.alignment.center, width=200, height=200)
        ], alignment=ft.alignment.center)

        meta_text.value = f"Meta mensal: {fmt(META_GLOBAL)}"

        # Chips de resumo
        resumo_row.controls.clear()
        for label, valor in [("Comprado", total_comprado), ("Pendente", total_gasto - total_comprado), ("Compras", float(qtd_compras))]:
            resumo_row.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text(fmt(valor) if label != "Compras" else str(qtd_compras),
                            color=TEXT_PRIMARY, size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(label, color=TEXT_SECONDARY, size=10, text_align=ft.TextAlign.CENTER),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=CARD_COLOR,
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
            ))

        # Lista de categorias reais
        list_content.controls.clear()
        if not categorias:
            list_content.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, color=TEXT_SECONDARY, size=40),
                    ft.Text("Nenhum item comprado ainda.", color=TEXT_SECONDARY, size=13, text_align=ft.TextAlign.CENTER),
                    ft.Text("Escaneie um recibo NF-e para ver os gastos por categoria.", color=TEXT_SECONDARY, size=11, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                alignment=ft.alignment.center,
                padding=30
            ))
        else:
            for c in categorias:
                list_content.controls.append(
                    build_category_row(c["categoria"], c["total"], total_comprado, c["qtd_itens"])
                )

        list_content.controls.append(ft.Container(height=60))
        view.update()

    page.run_task(perform_load_data)
    return view
