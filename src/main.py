import flet as ft
from accepter import LcuHandler
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

lcu = LcuHandler()

def main(page: ft.Page):
    page.title = "AutoAccepter v2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    button_text_start = "Iniciar Auto Accepter"
    button_text_stop = "Detener Auto Accepter"
    status_text = ft.Text(lcu.status_message) # Use initial LCU message

    async def update_status_periodically():
        while True:
            if status_text.value != lcu.status_message:
                status_text.value = lcu.status_message
                page.update()
            await asyncio.sleep(0.5) # UI status update frequency

    async def button_click_handler(e):
        # status_message is updated within lcu.toggle_auto_accept_loop and lcu.reinitialize
        # so it's not necessary to set it explicitly here before those calls.
        if not lcu.is_connected:
            logger.info("Auto-Accepter: Attempting to reconnect with LCU...")
            lcu.reinitialize() 
            # Force immediate status update after reinitialize
            status_text.value = lcu.status_message
            page.update()

        if lcu.is_connected:
            await lcu.toggle_auto_accept_loop() # This updates lcu.status_message internally
            if lcu.accepter_running:
                button.text = button_text_stop
            else:
                button.text = button_text_start
            logger.info(f"Auto-Accepter: Current state -> {lcu.status_message}")
        else:
            button.text = button_text_start
            logger.warning(f"Auto-Accepter: Not connected to LCU. Loop will not start/stop. Status: {lcu.status_message}")
        
        # Update status text and button
        status_text.value = lcu.status_message
        page.update()
            
    button = ft.ElevatedButton(
        text=button_text_start,
        on_click=button_click_handler
    )

    # Initial button text and status setup
    if lcu.is_connected and lcu.accepter_running:
        button.text = button_text_stop
    else:
        button.text = button_text_start
    status_text.value = lcu.status_message # Ensure correct initial state

    page.add(
        ft.Column(
            [
                status_text,
                button
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )
    
    # Start the periodic status update task in the background
    page.run_task(update_status_periodically)


ft.app(target=main, assets_dir="assets", view=ft.AppView.FLET_APP_HIDDEN)