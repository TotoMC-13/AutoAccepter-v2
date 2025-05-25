import aiohttp
import asyncio
import os
import platform
import json
import logging

# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LCU_READY_CHECK_ENDPOINT = "/lol-matchmaking/v1/ready-check"
LCU_ACCEPT_ENDPOINT = "/lol-matchmaking/v1/ready-check/accept"
LCU_GAMEFLOW_STATE_ENDPOINT = "/lol-gameflow/v1/gameflow-phase"

class LcuHandler:
    def __init__(self):
        self.lockfile_path = self.set_lockfile_path()
        self.status_message = "Inicializando..."
        self.lockfile_data = self.read_lol_lockfile_data() # This sets self.is_connected
        self.accepter_running = False
        self._accepter_task = None
        self.session = None

        if self.is_connected and self.lockfile_data:
            self.password = self.lockfile_data["password"]
            self.base_url, self.headers = self.get_lcu_connection_details()
            self.auth = aiohttp.BasicAuth('riot', self.password)
            self.status_message = "LCU Conectado. Listo."
        else:
            self.password = None
            self.base_url = None
            self.headers = None
            self.auth = None
            self.status_message = "LCU Desconectado. Verifica que LoL esté en ejecución."
            logger.error("Auto-Accepter: Fallo al inicializar los detalles de la conexion con LCU.")
        
    def reinitialize(self):
        logger.info("Auto-Accepter: Re-attempting LCU connection...")
        self.status_message = "Reconectando con LCU..."
        self.is_connected = False
        self.lockfile_data = None
        self.password = None
        self.base_url = None
        self.headers = None
        self.auth = None
        
        self.lockfile_path = self.set_lockfile_path()
        self.lockfile_data = self.read_lol_lockfile_data()

        if self.is_connected and self.lockfile_data:
            self.password = self.lockfile_data["password"]
            self.base_url, self.headers = self.get_lcu_connection_details()
            self.auth = aiohttp.BasicAuth('riot', self.password)
            self.status_message = "LCU Reconectado. Listo."
            logger.info("Auto-Accepter: Successfully re-initialized LCU details.")
        else:
            self.password = None
            self.base_url = None
            self.headers = None
            self.auth = None
            self.status_message = "Fallo al reconectar. Verifica que LoL esté en ejecución."
            logger.error("Auto-Accepter: Failed to re-initialize LCU details. LCU might not be running or lockfile is inaccessible.")

    async def _ensure_session_started(self):
        if not self.session or self.session.closed:
            if self.is_connected and self.auth and self.headers:
                connector = aiohttp.TCPConnector(ssl=False)
                self.session = aiohttp.ClientSession(connector=connector, auth=self.auth, headers=self.headers)
                logger.info("Auto-Accepter: Session (re)started.")
            else:
                self.status_message = "Error: No se pudo iniciar sesión LCU (detalles faltantes)."
                logger.error("Auto-Accepter: Cannot start session, LCU details missing.")
                return False
        return True

    async def _close_session_if_exists(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info("Auto-Accepter: Session closed.")

    def set_lockfile_path(self):
        system = platform.system()
        if system == "Windows":
            lol_path = r"D:\\Riot Games\\League of Legends\\lockfile"
            if os.path.exists(lol_path):
                return lol_path
            
            logger.warning("Lockfile no encontrado en D:\\\\Riot Games\\\\League of Legends\\\\lockfile.")
            return None
    
    def read_lol_lockfile_data(self):
        if not self.lockfile_path or not os.path.exists(self.lockfile_path):
            self.is_connected = False
            return None
        try:
            with open(self.lockfile_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            parts = content.split(':')
            if len(parts) == 5:
                data = {
                    "process_name": parts[0], "process_id": int(parts[1]),
                    "port": int(parts[2]), "password": parts[3], "protocol": parts[4]
                }
                self.is_connected = True
                return data
            else:
                self.is_connected = False
                return None
        except (IOError, ValueError):
            self.is_connected = False
            return None
        
    def get_lcu_connection_details(self):
        protocol = self.lockfile_data['protocol']
        port = self.lockfile_data['port']
        
        base_url = f"{protocol}://127.0.0.1:{port}"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

        return base_url, headers
    
    async def make_request(self, endpoint, method="GET", json_payload=None):
        if not self.is_connected:
            self.status_message = "Error: LCU no conectado para request."
            logger.warning("Auto-Accepter: No se pudo hacer el request, LCU no conectado.")
            return None, None
        
        if not await self._ensure_session_started():
             self.status_message = "Error: Sesión LCU no activa para request."
             logger.warning("Auto-Accepter: No se pudo hacer el request, sesión no activa.")
             return None, None
            
        complete_url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, complete_url, json=json_payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_json = await response.json()
                return response, response_json
        except aiohttp.ClientError as e:
            self.status_message = f"Error de red: {e}"
            logger.error(f"Request failed: {e}")
            return None, None
        except asyncio.TimeoutError:
            self.status_message = "Error: Timeout en request a LCU."
            logger.error(f"Request timed out: {method} {complete_url}")
            return None, None
        except Exception as e:
            self.status_message = f"Error inesperado en request: {e}"
            logger.error(f"An unexpected error occurred during request: {e}")
            await self._close_session_if_exists()
            return None, None

    async def run_auto_accept_loop(self):
        if not self.is_connected:
            self.status_message = "Error: LCU no conectado al iniciar bucle."
            logger.error("Auto-Accepter: No se pudo ejecutar el bucle, LCU no conectado.")
            self.accepter_running = False
            return

        if not await self._ensure_session_started():
            self.status_message = "Error: Fallo al iniciar sesión para el bucle."
            logger.error("Auto-Accepter: No se pudo iniciar la sesión para el bucle.")
            self.accepter_running = False
            return
        
        self.accepter_running = True
        self.status_message = "Auto-Accepter activo. Monitoreando..."
        logger.info("Auto-Accepter: Bucle interno iniciado.")

        try:
            while self.accepter_running:
                if not self.is_connected:
                    self.status_message = "LCU desconectado. Intentando reconectar..."
                    logger.warning("Auto-Accepter: LCU desconectado durante el bucle. Intentando reconectar...")
                    self.reinitialize() # This updates status_message
                    if not self.is_connected:
                        self.status_message = "Fallo al reconectar. Auto-Accepter detenido."
                        logger.error("Auto-Accepter: Falla al reconectar. Deteniendo bucle.")
                        self.accepter_running = False
                        break
                    else:
                        if not await self._ensure_session_started():
                            self.status_message = "Error: Fallo al reiniciar sesión tras reconexión."
                            logger.error("Auto-Accepter: Falla al reiniciar sesión tras reconexión. Deteniendo bucle.")
                            self.accepter_running = False
                            break
                
                _, gameflow_json = await self.make_request(LCU_GAMEFLOW_STATE_ENDPOINT)
            
                if not self.accepter_running: break

                if not gameflow_json:
                    self.status_message = "Esperando estado del juego..."
                elif gameflow_json == 'Lobby':
                    self.status_message = "En lobby."
                elif gameflow_json == "Matchmaking":
                    self.status_message = "Buscando partida..."
                elif gameflow_json == "ReadyCheck":
                    self.status_message = "¡Partida encontrada!"
                    _, ready_check_json = await self.make_request(LCU_READY_CHECK_ENDPOINT)
                    if not self.accepter_running: break 

                    if ready_check_json and ready_check_json.get("state") == "InProgress":            
                        self.status_message = "Aceptando partida..."
                        logger.info("Auto-Accepter: Partida encontrada, aceptando...")
                        await self.make_request(LCU_ACCEPT_ENDPOINT, method="POST")
                        self.status_message = "Partida aceptada."
                        logger.info("Auto-Accepter: Partida aceptada.")
                elif gameflow_json == "InProgress":
                    self.status_message = "Partida en progreso. Auto-Accepter detenido."
                    logger.info("Partida en progreso. Deteniendo auto-accepter.")
                    self.accepter_running = False # Stop the loop if theres a game in progress
                else:
                    self.status_message = f"Estado desconocido: {gameflow_json}"


                await asyncio.sleep(2)
        except Exception as e:
            self.status_message = f"Error en bucle: {e}"
            logger.exception("Auto-Accepter: Unexpected error in the main loop:") # logger.exception includes the traceback
        finally:
            logger.info("Auto-Accepter: Inner loop finished.")
            await self._close_session_if_exists()
            if self.accepter_running : # This means the loop ended due to an error, not a normal stop
                 self.status_message = "Auto-Accepter stopped due to error."
            self.accepter_running = False

    async def toggle_auto_accept_loop(self):
        if not self.accepter_running:
            self.status_message = "Iniciando Auto-Accepter..."
            if not self.is_connected:
                logger.info("Auto-Accepter: LCU no conectado. Intentando inicializar...")
                self.reinitialize()
            
            if not self.is_connected:
                logger.error("Auto-Accepter: No se puede iniciar el bucle, LCU sigue sin conectar.")
                if self.accepter_running:
                    self.accepter_running = False
                return

            self.accepter_running = True 
            logger.info("Auto-Accepter: Solicitando inicio del bucle...")
            self._accepter_task = asyncio.create_task(self.run_auto_accept_loop())
        else:
            if self._accepter_task:
                self.status_message = "Deteniendo Auto-Accepter..."
                logger.info("Auto-Accepter: Intentando detener el bucle...")
                self.accepter_running = False
                try:
                    await asyncio.wait_for(self._accepter_task, timeout=7.0) 
                    self.status_message = "Auto-Accepter detenido." # User-facing message, can remain in Spanish
                    logger.info("Auto-Accepter: Loop stopped successfully.")
                except asyncio.TimeoutError:
                    self.status_message = "Auto-Accepter detenido (timeout)." # User-facing message
                    logger.warning("Auto-Accepter: Loop did not stop in time, forcing cancellation...")
                    self._accepter_task.cancel()
                    try:
                        await self._accepter_task
                    except asyncio.CancelledError:
                        logger.info("Auto-Accepter: Loop task cancelled forcefully.")
                except asyncio.CancelledError:
                     self.status_message = "Auto-Accepter detenido (cancelado)." # User-facing message
                     logger.info("Auto-Accepter: Loop task was already cancelled.")
                except Exception as e:
                    self.status_message = f"Error al detener: {e}" # User-facing message
                    logger.exception("Auto-Accepter: Unexpected error while trying to stop the task:") # logger.exception includes the traceback
                finally:
                    self._accepter_task = None
            else:
                self.status_message = "Error: Estado inconsistente al detener."
                logger.error("Auto-Accepter: Estado inconsistente - accepter_running es True pero no hay tarea. Reseteando.")
                self.accepter_running = False
                await self._close_session_if_exists()