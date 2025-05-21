import flet as ft
from accepter import LcuHandler

lcu = LcuHandler()

def main(page: ft.Page):
    page.title = "AutoAccepter v2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER # Para centrar visualmente
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Para centrar visualmente

    async def button_click_handler(e): # Definir una función async separada para mayor claridad
        await lcu.toggle_auto_accept_loop()

    button = ft.ElevatedButton(text="Test!", on_click=button_click_handler) # Esto NO funciona, falta arreglarlo.
    page.add(button)

ft.app(target=main, assets_dir="assets")