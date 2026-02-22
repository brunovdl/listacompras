import flet as ft
from app_colors import BG_COLOR
from views.lista_view import get_lista_view
from views.historico_view import get_historico_view
from views.orcamento_view import get_orcamento_view
from views.add_item_view import get_add_item_view

def main(page: ft.Page):
    page.title = "Lista de Compras"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_COLOR
    
    # Customizing fonts, we assume default unless specified
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Inter")

    def route_change(route):
        page.views.clear()
        
        if page.route == "/lista":
            page.views.append(get_lista_view(page))
        elif page.route == "/historico":
            page.views.append(get_historico_view(page))
        elif page.route == "/orcamento":
            page.views.append(get_orcamento_view(page))
        elif page.route == "/add_item":
            page.views.append(get_add_item_view(page))
        else:
            page.views.append(get_lista_view(page))
            
        page.update()

    page.on_route_change = route_change
    page.go("/lista")

if __name__ == "__main__":
    import os
    os.environ["FLET_SECRET_KEY"] = "my_super_secret_key"
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, host="192.168.1.137", port=8000, upload_dir="uploads")
