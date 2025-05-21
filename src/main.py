import flet as ft
import time

def main(page: ft.Page):
    page.title = "AutoAccepter v2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER # Para centrar visualmente
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Para centrar visualmente

    def add_clicked(e):
        page.add(ft.Checkbox(label=new_task.value))
        new_task.value = ""
        new_task.focus()
        new_task.update()

    new_task = ft.TextField(label="What's needs to be done?", width=300)

    page.add(
        ft.Column(
            [
                new_task,
                ft.ElevatedButton("Add", on_click=add_clicked),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )

ft.app(target=main, assets_dir="assets")