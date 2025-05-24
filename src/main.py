import flet as ft
from accepter import LcuHandler
import asyncio

lcu = LcuHandler()

def main(page: ft.Page):
    page.title = "AutoAccepter v2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    button_text_start = "Iniciar Auto Accepter"
    button_text_stop = "Detener Auto Accepter"

    async def button_click_handler(e):
        if not lcu.is_connected:
            print("Auto-Accepter: Intentando reconectar con LCU...")
            lcu.reinitialize()

        if lcu.is_connected:
            await lcu.toggle_auto_accept_loop()
            if lcu.accepter_running:
                button.text = button_text_stop
                print("Auto-Accepter: Estado actual -> Corriendo")
            else:
                button.text = button_text_start
                print("Auto-Accepter: Estado actual -> Detenido")
        else:
            button.text = button_text_start
            print("Auto-Accepter: No conectado a LCU. El bucle no se iniciará/detendrá.")
        page.update()
            

    button = ft.ElevatedButton(
        text=button_text_start,  # Texto inicial
        on_click=button_click_handler
    )
    page.add(button)
    if lcu.is_connected and lcu.accepter_running:
        button.text = button_text_stop
    else:
        button.text = button_text_start
    page.update()


ft.app(target=main, assets_dir="assets")