import flet as ft
import asyncio
from app_colors import BG_COLOR, CARD_COLOR, CARD_ELEVATED, CYAN, TEXT_PRIMARY, TEXT_SECONDARY
from database import get_itens_lista, toggle_item_comprado, delete_item, update_item, supabase
from components.navbar import create_navbar

def get_lista_view(page: ft.Page):
    # Header area
    settings_icon = ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=TEXT_SECONDARY, icon_size=28)
    
    subtitle_text = ft.Text("Carregando itens...", size=12, color=TEXT_SECONDARY)

    # --- Estado de seleção múltipla ---
    selecao_ativa = [False]   # lista mutável para closure
    ids_selecionados = set()
    todos_os_ids = []

    def toggle_selecao_modo():
        selecao_ativa[0] = not selecao_ativa[0]
        ids_selecionados.clear()
        if selecao_ativa[0]:
            btn_selecionar.icon = ft.Icons.CLOSE
            btn_selecionar.icon_color = ft.Colors.RED_400
            selecao_bar.visible = True
            fab.visible = False
        else:
            btn_selecionar.icon = ft.Icons.CHECKLIST_OUTLINED
            btn_selecionar.icon_color = TEXT_SECONDARY
            selecao_bar.visible = False
            fab.visible = True
        page.run_task(perform_load_data)

    btn_selecionar = ft.IconButton(
        icon=ft.Icons.CHECKLIST_OUTLINED,
        icon_color=TEXT_SECONDARY,
        icon_size=24,
        tooltip="Selecionar itens",
        on_click=lambda e: toggle_selecao_modo()
    )
    settings_icon = ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=TEXT_SECONDARY, icon_size=28)

    header_col = ft.Column([
        ft.Row([
            ft.Text("Lista de Compras", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ft.Row([btn_selecionar, settings_icon], spacing=0)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        subtitle_text
    ], spacing=0)

    # Adicionar com IA
    ia_title = ft.Row([
        ft.Text("ADICIONAR COM IA", size=11, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
        ft.Container(
            content=ft.Text("BETA", size=9, weight=ft.FontWeight.BOLD, color=BG_COLOR),
            bgcolor=CYAN,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border_radius=4
        )
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Banner/barra de progresso do scanner (inline)
    scan_progress = ft.ProgressBar(width=float('inf'), color=CYAN, bgcolor=CARD_COLOR, visible=False)
    scan_status_text = ft.Text("", size=12, color=TEXT_SECONDARY)
    scan_banner = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, color=CYAN, size=16),
                scan_status_text
            ], spacing=6),
            scan_progress
        ], spacing=6),
        bgcolor=CARD_COLOR,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        visible=False
    )

    async def groq_file_scan(file_path):
        # Mostrar banner inline sem sair da view
        scan_status_text.value = "IA analisando a imagem..."
        scan_progress.value = None  # indeterminate
        scan_banner.visible = True
        scan_progress.visible = True
        view.update()
        
        try:
            from groq_service import analyze_receipt_or_list_with_groq
            from database import insert_itens_mock
            
            mock_items = await asyncio.to_thread(analyze_receipt_or_list_with_groq, file_path)
            
            if mock_items and len(mock_items) > 0:
                total = len(mock_items)
                for idx, item in enumerate(mock_items):
                    item['comprado'] = False
                    item.setdefault('preco', 0.0)
                    # Inserir um item de cada vez
                    await insert_itens_mock([item])
                    scan_status_text.value = f"Adicionando itens... {idx+1}/{total}"
                    scan_progress.value = (idx + 1) / total
                    # Atualizar lista sem reconstruir a view inteira
                    await perform_load_data()
                
                scan_status_text.value = f"✅ {total} itens adicionados!"
                scan_progress.visible = False
                view.update()
                await asyncio.sleep(2)
            else:
                scan_status_text.value = "Nenhum item reconhecido na imagem."
                scan_progress.visible = False
                view.update()
                await asyncio.sleep(2)
                
        except Exception as ex:
            print(f"Erro no scanner: {ex}")
            scan_status_text.value = f"⚠️ Erro: verifique o terminal."
            scan_progress.visible = False
            view.update()
            await asyncio.sleep(3)
        
        scan_banner.visible = False
        view.update()

    async def qr_file_scan(file_path):
        """Scanner via QR Code de NF-e"""
        scan_status_text.value = "Lendo QR Code da nota fiscal..."
        scan_progress.value = None  # indeterminate
        scan_banner.visible = True
        scan_progress.visible = True
        view.update()

        try:
            from qrcode_service import get_items_from_nfe_qrcode
            from database import insert_itens_mock

            nfe_items = await asyncio.to_thread(get_items_from_nfe_qrcode, file_path)

            if nfe_items and len(nfe_items) > 0:
                total = len(nfe_items)
                for idx, item in enumerate(nfe_items):
                    item.setdefault('comprado', False)
                    item.setdefault('preco', 0.0)
                    await insert_itens_mock([item])
                    scan_status_text.value = f"Importando itens da nota... {idx+1}/{total}"
                    scan_progress.value = (idx + 1) / total
                    await perform_load_data()

                scan_status_text.value = f"✅ {total} itens importados da NF-e!"
                scan_progress.visible = False
                view.update()
                await asyncio.sleep(2)
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

    def on_file_uploaded(e: ft.FilePickerUploadEvent):
        if e.progress == 1.0:
            import os
            file_path = os.path.join("uploads", e.file_name)
            page.run_task(groq_file_scan, file_path)

    def on_file_uploaded_qr(e: ft.FilePickerUploadEvent):
        if e.progress == 1.0:
            import os
            file_path = os.path.join("uploads", e.file_name)
            page.run_task(qr_file_scan, file_path)

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path:
                page.run_task(groq_file_scan, file_path)
            else:
                uf = []
                for f in e.files:
                    try:
                        uf.append(
                            ft.FilePickerUploadFile(
                                f.name,
                                upload_url=page.get_upload_url(f.name, 60)
                            )
                        )
                    except Exception as ex:
                        print("Erro get_upload_url:", ex)
                        sb = ft.SnackBar(ft.Text(f"Erro no upload: {ex}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
                        page.overlay.append(sb)
                        page.update()
                        return
                file_picker.upload(uf)

    def on_file_picked_qr(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path:
                page.run_task(qr_file_scan, file_path)
            else:
                uf = []
                for f in e.files:
                    try:
                        uf.append(
                            ft.FilePickerUploadFile(
                                f.name,
                                upload_url=page.get_upload_url(f.name, 60)
                            )
                        )
                    except Exception as ex:
                        print("Erro get_upload_url (QR):", ex)
                        sb = ft.SnackBar(ft.Text(f"Erro no upload: {ex}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
                        page.overlay.append(sb)
                        page.update()
                        return
                file_picker_qr.upload(uf)

    file_picker = ft.FilePicker(on_result=on_file_picked, on_upload=on_file_uploaded)
    file_picker_qr = ft.FilePicker(on_result=on_file_picked_qr, on_upload=on_file_uploaded_qr)

    btn_escanear_lista = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.DOCUMENT_SCANNER_OUTLINED, color=CYAN, size=40),
            ft.Text("Escanear Lista", size=14, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        bgcolor=CARD_COLOR,
        border_radius=12,
        height=100,
        expand=True,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False),
        ink=True
    )
    
    btn_escanear_recibo = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, color=CYAN, size=40),
            ft.Text("Escanear Recibo", size=14, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        bgcolor=CARD_COLOR,
        border_radius=12,
        height=100,
        expand=True,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False),
        ink=True
    )

    btn_qrcode = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.QR_CODE_SCANNER, color=CYAN, size=40),
            ft.Text("QR Code NF-e", size=14, color=TEXT_PRIMARY, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        bgcolor=CARD_COLOR,
        border_radius=12,
        height=100,
        expand=True,
        on_click=lambda _: file_picker_qr.pick_files(allow_multiple=False),
        ink=True
    )

    ia_row = ft.Row([btn_escanear_lista, btn_escanear_recibo, btn_qrcode], spacing=10)

    ia_section = ft.Column([
        ia_title,
        ia_row
    ], spacing=12)

    # Categories Content
    list_content = ft.Column(scroll=ft.ScrollMode.HIDDEN, expand=True, spacing=20)

    main_container = ft.Container(
        content=ft.Column([
            header_col,
            ft.Container(height=10),
            ia_section,
            ft.Container(height=10),
            scan_banner,
            list_content,
        ], expand=True),
        expand=True,
        padding=ft.padding.only(left=20, right=20, top=40, bottom=0),
        bgcolor=BG_COLOR
    )

    # Barra de seleção múltipla
    sel_count_text = ft.Text("0 selecionados", color=TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500)

    async def selecionar_todos(e):
        if len(ids_selecionados) == len(todos_os_ids):
            ids_selecionados.clear()
        else:
            ids_selecionados.clear()
            ids_selecionados.update(todos_os_ids)
        await perform_load_data()

    async def excluir_selecionados(e):
        if not ids_selecionados:
            return

        async def do_delete(dlg):
            dlg.open = False
            page.update()
            import asyncio as aio
            tasks = [delete_item(iid) for iid in list(ids_selecionados)]
            await aio.gather(*tasks)
            ids_selecionados.clear()
            toggle_selecao_modo()  # desativa modo

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Excluir {len(ids_selecionados)} item(ns)?", color=TEXT_PRIMARY),
            content=ft.Text("Esta ação não pode ser desfeita.", color=TEXT_SECONDARY),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, 'open', False) or page.update()),
                ft.TextButton(
                    "Excluir",
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                    on_click=lambda e: page.run_task(do_delete, dlg)
                ),
            ],
            bgcolor=CARD_COLOR,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    selecao_bar = ft.Container(
        content=ft.Row([
            sel_count_text,
            ft.Row([
                ft.TextButton(
                    "Todos",
                    icon=ft.Icons.SELECT_ALL,
                    icon_color=CYAN,
                    style=ft.ButtonStyle(color=CYAN),
                    on_click=lambda e: page.run_task(selecionar_todos, e)
                ),
                ft.TextButton(
                    "Excluir",
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                    on_click=lambda e: page.run_task(excluir_selecionados, e)
                ),
            ], spacing=0)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=CARD_COLOR,
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        visible=False,
        border_radius=ft.border_radius.only(top_left=16, top_right=16)
    )

    nav_bar = create_navbar(page, 0)

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=CYAN,
        on_click=lambda _: page.go("/add_item"),
        shape=ft.CircleBorder()
    )

    view = ft.View(
        "/lista",
        [
            main_container,
            selecao_bar,
            nav_bar
        ],
        bgcolor=BG_COLOR,
        padding=0,
        floating_action_button=fab,
    )
    view.controls.append(file_picker)
    view.controls.append(file_picker_qr)

    async def on_checkbox_change(e, item_id, current_status):
        new_status = not current_status
        e.control.disabled = True
        view.update()
        sucesso = await toggle_item_comprado(item_id, new_status)
        if sucesso:
            await perform_load_data()
        else:
            e.control.disabled = False
            e.control.value = current_status
            view.update()

    CARD_COLOR_COMPRADO = "#0D1A26"

    def build_item_card(item):
        nome = item.get('nome', 'Sem nome')
        preco = item.get('preco', 0)
        categoria = item.get('categoria', '')
        item_id = item.get('id')
        is_comprado = item.get('comprado', False)

        text_decor = ft.TextDecoration.LINE_THROUGH if is_comprado else ft.TextDecoration.NONE
        text_color = TEXT_SECONDARY if is_comprado else TEXT_PRIMARY

        # --- Modo de seleção múltipla ---
        if selecao_ativa[0]:
            is_sel = item_id in ids_selecionados

            def toggle_select(e, iid=item_id):
                if iid in ids_selecionados:
                    ids_selecionados.discard(iid)
                else:
                    ids_selecionados.add(iid)
                sel_count_text.value = f"{len(ids_selecionados)} selecionado(s)"
                page.run_task(perform_load_data)

            sel_cb = ft.Checkbox(
                value=is_sel,
                fill_color={ft.ControlState.SELECTED: ft.Colors.RED_400, ft.ControlState.DEFAULT: "transparent"},
                check_color=ft.Colors.WHITE,
                on_change=toggle_select
            )

            return ft.Container(
                content=ft.Row([
                    sel_cb,
                    ft.Column([
                        ft.Text(nome, color=text_color, size=14, weight=ft.FontWeight.W_500, style=ft.TextStyle(decoration=text_decor)),
                        ft.Text(categoria if categoria else "1 un", color=TEXT_SECONDARY, size=11)
                    ], expand=True, spacing=2),
                    ft.Text(f"R$ {preco:.2f}", color=ft.Colors.RED_400 if is_sel else text_color, size=13, weight=ft.FontWeight.W_600),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_400) if is_sel else (CARD_COLOR_COMPRADO if is_comprado else CARD_COLOR),
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=10, vertical=10),
                border=ft.border.all(1, ft.Colors.RED_400) if is_sel else None,
                on_click=lambda e, iid=item_id: toggle_select(e, iid)
            )

        # --- Modo normal ---
        cb = ft.Checkbox(
            value=is_comprado,
            fill_color={ft.ControlState.SELECTED: CYAN, ft.ControlState.DEFAULT: "transparent"},
            check_color=BG_COLOR,
            on_change=lambda e: page.run_task(on_checkbox_change, e, item_id, is_comprado)
        )

        async def confirmar_exclusao(e):
            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Excluir item?", color=TEXT_PRIMARY),
                content=ft.Text(f"Tem certeza que deseja excluir \"{nome}\"?", color=TEXT_SECONDARY),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: close_dlg(dlg)),
                    ft.TextButton(
                        "Excluir",
                        style=ft.ButtonStyle(color=ft.Colors.RED_400),
                        on_click=lambda e: page.run_task(fazer_exclusao, dlg)
                    ),
                ],
                bgcolor=CARD_COLOR,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def close_dlg(dlg):
            dlg.open = False
            page.update()

        async def fazer_exclusao(dlg):
            close_dlg(dlg)
            sucesso = await delete_item(item_id)
            if sucesso:
                await perform_load_data()
            else:
                sb = ft.SnackBar(ft.Text("Erro ao excluir item", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
                page.overlay.append(sb)
                page.update()

        async def abrir_edicao(e):
            txt_nome = ft.TextField(
                value=nome, label="Nome",
                border_color=CYAN, label_style=ft.TextStyle(color=TEXT_SECONDARY),
                color=TEXT_PRIMARY, bgcolor=CARD_COLOR, border_radius=8
            )
            txt_preco = ft.TextField(
                value=str(preco), label="Preço (R$)",
                border_color=CYAN, label_style=ft.TextStyle(color=TEXT_SECONDARY),
                color=TEXT_PRIMARY, bgcolor=CARD_COLOR, border_radius=8,
                keyboard_type=ft.KeyboardType.NUMBER
            )
            dd_cat = ft.Dropdown(
                value=categoria if categoria else "Mercado",
                options=[
                    ft.dropdown.Option("Mercado"),
                    ft.dropdown.Option("Hortifruti"),
                    ft.dropdown.Option("Limpeza"),
                    ft.dropdown.Option("Açougue"),
                    ft.dropdown.Option("Outros"),
                ],
                border_color=CYAN, label="Categoria", label_style=ft.TextStyle(color=TEXT_SECONDARY),
                color=TEXT_PRIMARY, bgcolor=CARD_COLOR, border_radius=8
            )

            dlg_edit = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar item", color=TEXT_PRIMARY),
                content=ft.Column([
                    txt_nome,
                    txt_preco,
                    dd_cat
                ], tight=True, spacing=12),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: close_dlg(dlg_edit)),
                    ft.TextButton(
                        "Salvar",
                        style=ft.ButtonStyle(color=CYAN),
                        on_click=lambda e: page.run_task(salvar_edicao, dlg_edit, txt_nome, txt_preco, dd_cat)
                    ),
                ],
                bgcolor=CARD_COLOR,
            )
            page.overlay.append(dlg_edit)
            dlg_edit.open = True
            page.update()

        async def salvar_edicao(dlg, txt_nome, txt_preco, dd_cat):
            try:
                novo_preco = float(txt_preco.value.replace(",", ".")) if txt_preco.value else 0.0
            except:
                novo_preco = 0.0
            dados = {
                "nome": txt_nome.value,
                "preco": novo_preco,
                "categoria": dd_cat.value
            }
            close_dlg(dlg)
            sucesso = await update_item(item_id, dados)
            if sucesso:
                await perform_load_data()
            else:
                sb = ft.SnackBar(ft.Text("Erro ao atualizar item", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED, open=True)
                page.overlay.append(sb)
                page.update()

        btn_edit = ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            icon_color=CYAN,
            icon_size=18,
            tooltip="Editar",
            on_click=lambda e: page.run_task(abrir_edicao, e),
            style=ft.ButtonStyle(padding=ft.padding.all(4))
        )
        btn_delete = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            icon_size=18,
            tooltip="Excluir",
            on_click=lambda e: page.run_task(confirmar_exclusao, e),
            style=ft.ButtonStyle(padding=ft.padding.all(4))
        )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    cb,
                    ft.Column([
                        ft.Text(nome, color=text_color, size=14, weight=ft.FontWeight.W_500, style=ft.TextStyle(decoration=text_decor)),
                        ft.Text(categoria if categoria else "1 un", color=TEXT_SECONDARY, size=11, style=ft.TextStyle(decoration=text_decor))
                    ], expand=True, spacing=2),
                    ft.Column([
                        ft.Text(f"R$ {preco:.2f}", color=text_color, size=13, weight=ft.FontWeight.W_600, style=ft.TextStyle(decoration=text_decor)),
                        ft.Text("Comprado" if is_comprado else "Pendente", color=CYAN if is_comprado else TEXT_SECONDARY, size=10, text_align=ft.TextAlign.RIGHT)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                    ft.Row([btn_edit, btn_delete], spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            bgcolor=CARD_COLOR_COMPRADO if is_comprado else CARD_COLOR,
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=10, vertical=10)
        )

    async def perform_load_data():
        itens = await get_itens_lista()
        list_content.controls.clear()

        # Atualizar lista de todos os ids para "Selecionar Todos"
        todos_os_ids.clear()
        todos_os_ids.extend([i['id'] for i in itens if i.get('id')])

        # Atualizar contador de seleção
        sel_count_text.value = f"{len(ids_selecionados)} selecionado(s)"

        if not itens:
            list_content.controls.append(ft.Container(
                content=ft.Text("Nenhum item na lista!", color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center,
                padding=40
            ))
            
            # update subtitle placeholder
            subtitle_text.value = "0 itens restantes - R$ 0,00 est."
            view.update()
            return
            
        itens_pendentes = [i for i in itens if not i.get('comprado', False)]
        itens_comprados = [i for i in itens if i.get('comprado', False)]
        
        total_est = sum([float(i.get('preco', 0)) for i in itens_pendentes])
        
        # Update subtitle
        subtitle_text.value = f"{len(itens_pendentes)} itens restantes • R$ {total_est:.2f} est."

        if itens_pendentes:
            # Mock category grouping
            cat_title = ft.Row([
                ft.Text("PENDENTES", size=11, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                ft.Text("Ordenar por Corredor", size=11, weight=ft.FontWeight.W_500, color=CYAN)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            
            list_content.controls.append(cat_title)
            
            for item in itens_pendentes:
                list_content.controls.append(build_item_card(item))
                
        if itens_comprados:
            list_content.controls.append(ft.Container(height=10))
            list_content.controls.append(ft.Divider(height=1, color=TEXT_SECONDARY)) 
            list_content.controls.append(ft.Container(height=10))
            
            list_content.controls.append(ft.Row([
                ft.Text("COMPRADOS", size=11, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            
            for item in itens_comprados:
                list_content.controls.append(build_item_card(item))
            
        # Add some bottom padding so FAB doesn't hide last item
        list_content.controls.append(ft.Container(height=80))

        view.update()

    async def load_data(*args):
        await perform_load_data()
        
    page.run_task(load_data)
    return view
