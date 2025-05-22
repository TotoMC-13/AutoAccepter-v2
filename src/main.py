import flet as ft
from accepter import LcuHandler
import asyncio

def main(page: ft.Page):
    page.title = "AutoAccepter v2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER # Para centrar visualmente
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Para centrar visualmente

    async def button_click_handler(e): # Definir una función async separada para mayor claridad
        async with LcuHandler() as lcu:
            if lcu.is_connected:
                await lcu.toggle_auto_accept_loop()
                if lcu._accepter_task:
                    try:
                        await lcu._accepter_task
                    except asyncio.CancelledError:
                        print("Auto-Accepter: Tarea principal cancelada (ej. por Ctrl+C o cierre del programa).")
                        if not lcu._accepter_task.done():
                            lcu._accepter_task.cancel()
                else:
                    print("Auto-Accepter: No se pudo iniciar la tarea del bucle.")
            else:
                print("Auto-Accepter: No conectado a LCU. El bucle no se iniciará.")

    button = ft.ElevatedButton(text="Test!", on_click=button_click_handler)
    page.add(button)

ft.app(target=main, assets_dir="assets")