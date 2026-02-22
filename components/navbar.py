import flet as ft
from app_colors import BG_COLOR, CYAN, TEXT_SECONDARY

def create_navbar(page: ft.Page, selected_index: int):
    def change_tab(index: int):
        if index == 0:
            page.go("/lista")
        elif index == 1:
            page.go("/historico")
        elif index == 2:
            page.go("/orcamento")

    return ft.CupertinoNavigationBar(
        bgcolor=BG_COLOR,
        active_color=CYAN,
        inactive_color=TEXT_SECONDARY,
        selected_index=selected_index,
        on_change=lambda e: change_tab(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT, label="Lista"),
            ft.NavigationBarDestination(icon=ft.Icons.HISTORY, label="Histórico"),
            ft.NavigationBarDestination(icon=ft.Icons.PIE_CHART, label="Orçamento"),
        ]
    )
