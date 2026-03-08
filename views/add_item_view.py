import flet as ft
from app_colors import BG_COLOR, CARD_COLOR, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import insert_item

def get_add_item_view(page: ft.Page, lista_id: int):
    # Header
    back_btn = ft.IconButton(
        icon=ft.Icons.ARROW_BACK_IOS_NEW,
        icon_color=TEXT_PRIMARY,
        on_click=lambda _: page.go(f"/lista/{lista_id}")
    )

    header_col = ft.Row([
        back_btn,
        ft.Text("Novo Item", size=20, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ft.Container(width=40)  # Spacer to center the title
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Inputs
    txt_nome = ft.TextField(
        label="Nome do Produto",
        hint_text="Ex: Leite, Maçã, Pão...",
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        focused_color=TEXT_PRIMARY,
        bgcolor=CARD_COLOR,
        border_radius=12,
        height=60,
        autofocus=True,
    )

    txt_categoria = ft.Dropdown(
        label="Categoria (Opcional)",
        options=[
            ft.dropdown.Option("Mercado"),
            ft.dropdown.Option("Hortifruti"),
            ft.dropdown.Option("Açougue"),
            ft.dropdown.Option("Limpeza"),
            ft.dropdown.Option("Padaria"),
            ft.dropdown.Option("Frios"),
            ft.dropdown.Option("Outros")
        ],
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        bgcolor=CARD_COLOR,
        border_radius=12,
        height=60
    )

    txt_preco = ft.TextField(
        label="Preço Estimado (R$)",
        hint_text="Ex: 5.50",
        color=TEXT_PRIMARY,
        border_color=CYAN,
        focused_border_color=CYAN,
        focused_color=TEXT_PRIMARY,
        bgcolor=CARD_COLOR,
        border_radius=12,
        keyboard_type=ft.KeyboardType.NUMBER,
        height=60
    )

    btn_salvar = ft.ElevatedButton(
        content=ft.Text("Adicionar à Lista", size=16, weight=ft.FontWeight.BOLD),
        bgcolor=CYAN,
        color=BG_COLOR,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        height=55,
        width=float('inf')
    )

    content_col = ft.Column([
        header_col,
        ft.Container(height=20),
        txt_nome,
        ft.Container(height=10),
        txt_categoria,
        ft.Container(height=10),
        txt_preco,
        ft.Container(height=30),
        btn_salvar
    ], expand=True)

    main_container = ft.Container(
        content=content_col,
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=20),
        bgcolor=BG_COLOR
    )

    view = ft.View(
        f"/add_item/{lista_id}",
        [main_container],
        bgcolor=BG_COLOR,
        padding=0
    )

    async def salvar_item(e):
        nome = txt_nome.value.strip() if txt_nome.value else ""
        if not nome:
            sb = ft.SnackBar(ft.Text("Preencha o nome do produto!", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
            page.overlay.append(sb)
            page.update()
            return

        try:
            preco_val = float(txt_preco.value.replace(",", ".")) if txt_preco.value else 0.0
        except Exception:
            sb = ft.SnackBar(ft.Text("Preço inválido!", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
            page.overlay.append(sb)
            page.update()
            return

        btn_salvar.disabled = True
        view.update()

        novo_item = {
            "nome": nome,
            "categoria": txt_categoria.value if txt_categoria.value else None,
            "preco": preco_val,
            "comprado": False,
            "lista_id": lista_id,
        }

        sucesso = await insert_item(novo_item)

        if sucesso:
            sb = ft.SnackBar(ft.Text("Item adicionado com sucesso!", color=BG_COLOR), bgcolor=CYAN, open=True)
            page.overlay.append(sb)
            page.update()
            page.go(f"/lista/{lista_id}")
        else:
            sb = ft.SnackBar(ft.Text("Erro ao salvar no banco", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
            page.overlay.append(sb)
            btn_salvar.disabled = False
            view.update()

    btn_salvar.on_click = lambda e: page.run_task(salvar_item, e)

    return view
