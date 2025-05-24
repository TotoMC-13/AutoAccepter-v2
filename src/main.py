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
            lcu.reinitialize() # Intenta reconectar si no está conectado

        if lcu.is_connected:
            await lcu.toggle_auto_accept_loop() # Esta función maneja el inicio/parada
            if lcu.accepter_running:
                button.text = button_text_stop
                print("Auto-Accepter: Estado actual -> Corriendo")
            else:
                button.text = button_text_start
                print("Auto-Accepter: Estado actual -> Detenido")
        else:
            button.text = button_text_start # Asegurar texto inicial si no hay conexión
            print("Auto-Accepter: No conectado a LCU. El bucle no se iniciará/detendrá.")
            # Podrías mostrar un diálogo de error al usuario aquí
            # page.show_dialog(...)
        page.update() # Actualiza la UI para mostrar el nuevo texto del botón
            

    button = ft.ElevatedButton(
        text=button_text_start,  # Texto inicial
        on_click=button_click_handler
    )
    page.add(button)

    # Inicializar el texto del botón según el estado actual de LCU al cargar la página
    # Esto es útil si el estado persiste entre reinicios de la UI (aunque aquí no lo hace)
    # o si el bucle podría estar corriendo desde una sesión anterior (no aplicable aquí directamente).
    # Principalmente asegura que el texto sea correcto al inicio.
    if lcu.is_connected and lcu.accepter_running:
        button.text = button_text_stop
    else:
        button.text = button_text_start
    page.update()


ft.app(target=main, assets_dir="assets")