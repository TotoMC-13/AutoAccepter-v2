import aiohttp
import asyncio
import os
import platform
import json

LCU_READY_CHECK_ENDPOINT = "/lol-matchmaking/v1/ready-check"
LCU_ACCEPT_ENDPOINT = "/lol-matchmaking/v1/ready-check/accept"
LCU_GAMEFLOW_STATE_ENDPOINT = "/lol-gameflow/v1/gameflow-phase"

class LcuHandler:
    def __init__(self):
        self.lockfile_path = self.set_lockfile_path()
        self.lockfile_data = self.read_lol_lockfile_data() # This sets self.is_connected
        self.accepter_running = False
        self._accepter_task = None
        self.session = None # Initialize session

        if self.is_connected and self.lockfile_data:
            self.password = self.lockfile_data["password"]
            self.base_url, self.headers = self.get_lcu_connection_details()
            self.auth = aiohttp.BasicAuth('riot', self.password)
        else:
            self.password = None
            self.base_url = None
            self.headers = None
            self.auth = None
            print("Auto-Accepter: Fallo al inicializar los detalles de la conexion con LCU.")
        


    def reinitialize(self):
        print("Auto-Accepter: Re-attempting LCU connection...")
        self.is_connected = False
        self.lockfile_data = None
        self.password = None
        self.base_url = None
        self.headers = None
        self.auth = None
        # Ensure session closes if it existed

        self.lockfile_path = self.set_lockfile_path()
        self.lockfile_data = self.read_lol_lockfile_data() # This sets self.is_connected

        if self.is_connected and self.lockfile_data:
            self.password = self.lockfile_data["password"]
            self.base_url, self.headers = self.get_lcu_connection_details()
            self.auth = aiohttp.BasicAuth('riot', self.password)
            print("Auto-Accepter: Successfully re-initialized LCU details.")
        else:
            self.password = None
            self.base_url = None
            self.headers = None
            self.auth = None
            print("Auto-Accepter: Failed to re-initialize LCU details. LCU might not be running or lockfile is inaccessible.")

    async def _ensure_session_started(self):
        if not self.session or self.session.closed:
            if self.is_connected and self.auth and self.headers:
                connector = aiohttp.TCPConnector(ssl=False)
                self.session = aiohttp.ClientSession(connector=connector, auth=self.auth, headers=self.headers)
                print("Auto-Accepter: Session (re)started.")
            else:
                print("Auto-Accepter: Cannot start session, LCU details missing.")
                return False
        return True

    async def _close_session_if_exists(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            print("Auto-Accepter: Session closed.")

    def set_lockfile_path(self):
        system = platform.system()
        if system == "Windows":
            lol_path = r"D:\Riot Games\League of Legends\lockfile"
            if os.path.exists(lol_path):
                return lol_path
            
            print("Lockfile no encontrado en D:\\Riot Games\\League of Legends\\lockfile.")
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
            print("Auto-Accepter: No se pudo hacer el request, LCU no conectado.")
            return None, None
        
        if not await self._ensure_session_started(): # Ensure session is active.
             print("Auto-Accepter: No se pudo hacer el request, sesión no activa.")
             return None, None
            
        complete_url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, complete_url, json=json_payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_json = await response.json()
                return response, response_json
        except aiohttp.ClientError as e:
            print(f"Request failed: {e}")
            # We could try to close and reopen the session in the next try
            # await self._close_session_if_exists() or handle this inside the loop.
            return None, None
        except asyncio.TimeoutError:
            print(f"Request timed out: {method} {complete_url}")
            return None, None
        except Exception as e:
            print(f"An unexpected error occurred during request: {e}")
            await self._close_session_if_exists() # Tries closing the session if an unexpected error happens.
            return None, None


    async def run_auto_accept_loop(self):
        if not self.is_connected:
            print("Auto-Accepter: No se pudo ejecutar el bucle, LCU no conectado.")
            self.accepter_running = False
            return

        if not await self._ensure_session_started():
            print("Auto-Accepter: No se pudo iniciar la sesión para el bucle.")
            self.accepter_running = False
            return
        
        self.accepter_running = True
        print("Auto-Accepter: Bucle interno iniciado.")

        try:
            while self.accepter_running:
                if not self.is_connected:
                    print("Auto-Accepter: LCU desconectado durante el bucle. Intentando reconectar...")
                    self.reinitialize()
                    if not self.is_connected:
                        print("Auto-Accepter: Falla al reconectar. Deteniendo bucle.")
                        self.accepter_running = False
                        break
                    else: # If it reconnects, re-ensure the session.
                        if not await self._ensure_session_started():
                            print("Auto-Accepter: Falla al reiniciar sesión tras reconexión. Deteniendo bucle.")
                            self.accepter_running = False
                            break
                
                _, gameflow_json = await self.make_request(LCU_GAMEFLOW_STATE_ENDPOINT)
            
                if not self.accepter_running: break # Quit if it stops during the request

                if not gameflow_json:
                    print("Auto-Accepter: No estas en un lobby o error de API, esperando.")
                elif gameflow_json == 'Lobby':
                    print("Auto-Accepter: Esperando en el lobby.")
                elif gameflow_json == "Matchmaking":
                    print("Auto-Accepter: Buscando partida.")

                if gameflow_json == "ReadyCheck":
                    _, ready_check_json = await self.make_request(LCU_READY_CHECK_ENDPOINT)
                    if not self.accepter_running: break 

                    if ready_check_json and ready_check_json.get("state") == "InProgress":            
                        print("Auto-Accepter: Partida encontrada, aceptando...")
                        await self.make_request(LCU_ACCEPT_ENDPOINT, method="POST")
                        print("Auto-Accepter: Partida aceptada.")
                elif gameflow_json == "InProgress":
                    print("Partida en progreso. Deteniendo auto-accepter temporalmente.")
                    self.accepter_running = False
            
                await asyncio.sleep(3)
        except Exception as e:
            print(f"Auto-Accepter: Error inesperado en el bucle principal: {e}")
        finally:
            print("Auto-Accepter: Bucle interno finalizado.")
            await self._close_session_if_exists()
            self.accepter_running = False # Asegurar que el estado es correcto al salir

    async def toggle_auto_accept_loop(self):
        if not self.accepter_running:
            if not self.is_connected:
                print("Auto-Accepter: LCU no conectado. Intentando inicializar...")
                self.reinitialize()
            
            if not self.is_connected:
                print("Auto-Accepter: No se puede iniciar el bucle, LCU sigue sin conectar.")
                if self.accepter_running: 
                    self.accepter_running = False
                return

            self.accepter_running = True 
            print("Auto-Accepter: Solicitando inicio del bucle...")
            self._accepter_task = asyncio.create_task(self.run_auto_accept_loop())
        else: # Its running and we want to stop it.
            if self._accepter_task:
                print("Auto-Accepter: Intentando detener el bucle...")
                self.accepter_running = False # Stop the loop.
                try:
                    # Dar tiempo al bucle para que termine limpiamente
                    await asyncio.wait_for(self._accepter_task, timeout=7.0) 
                    print("Auto-Accepter: Bucle detenido correctamente.")
                except asyncio.TimeoutError:
                    print("Auto-Accepter: El bucle no se detuvo a tiempo, forzando cancelación...")
                    self._accepter_task.cancel()
                    try:
                        await self._accepter_task # Waiting for it to stop.
                    except asyncio.CancelledError:
                        print("Auto-Accepter: Tarea del bucle cancelada forzosamente.")
                except asyncio.CancelledError: # If the task was already canceled.
                     print("Auto-Accepter: La tarea del bucle ya había sido cancelada.")
                except Exception as e:
                    print(f"Auto-Accepter: Error inesperado al intentar detener la tarea: {e}")
                finally:
                    self._accepter_task = None
                    # self.accepter_running already is false..
            else:
                print("Auto-Accepter: Estado inconsistente - accepter_running es True pero no hay tarea. Reseteando.")
                self.accepter_running = False
                await self._close_session_if_exists()
    
    def print_data(self):
        print(f"\n{self.lockfile_data}") # Ej: {'process_name': 'LeagueClient', 'process_id': 17968, 'port': 51308, 'password': 'mQr8OsqYuL-CP3DVr1msrQ', 'protocol': 'https'}