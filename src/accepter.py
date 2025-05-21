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

        if self.is_connected and self.lockfile_data:
            self.password = self.lockfile_data["password"]
            self.base_url, self.headers = self.get_lcu_connection_details()
            self.auth = aiohttp.BasicAuth('riot', self.password)
        else:
            self.password = None
            self.base_url = None
            self.headers = None
            self.auth = None
            # self.is_connected is already False from read_lol_lockfile_data
            print("Failed to initialize LCU connection details.")
        
        self.session = None


    async def __aenter__(self):
        if self.is_connected:
            # Disable SSL verification
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(connector=connector, auth=self.auth, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

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
        if not self.is_connected or not self.session:
            print("Cannot make request: LCU not connected or session not initialized.")
            return None, None
            
        complete_url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, complete_url, json=json_payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                # For debugging
                response_json = await response.json()
                # formatted_json = json.dumps(response_json, indent=2, ensure_ascii=False)
                # print(f"\n{formatted_json}")
                return response, response_json
        except aiohttp.ClientError as e:
            print(f"Request failed: {e}")
            return None, None
        except asyncio.TimeoutError:
            print(f"Request timed out: {method} {complete_url}")
            return None, None
    
    async def run_auto_accept_loop(self):
        if not self.is_connected:
            print("Cannot run auto accept loop: LCU not connected.")
            return
        
        self.accepter_running = True

        while self.accepter_running:
            _, gameflow_json = await self.make_request(LCU_GAMEFLOW_STATE_ENDPOINT)

            if gameflow_json == 'Lobby':
                print("Esperando en el lobby.")
            elif gameflow_json == "Matchmaking":
                print("Buscando partida.")

            if gameflow_json == "ReadyCheck":
                _, ready_check_json = await self.make_request(LCU_READY_CHECK_ENDPOINT)
                if ready_check_json["state"] == "InProgress":            
                    print("Partida encontrada, aceptando...")
                    await self.make_request(LCU_ACCEPT_ENDPOINT, method="POST")
                    print("Partida aceptada.")
            
            await asyncio.sleep(3)
        
        print("El autoaccepter se detuvo exitosamente.")
    
    def print_data(self):
        print(f"\n{self.lockfile_data}") # Ej: {'process_name': 'LeagueClient', 'process_id': 17968, 'port': 51308, 'password': 'mQr8OsqYuL-CP3DVr1msrQ', 'protocol': 'https'}

async def main():
    async with LcuHandler() as lcu:
        if lcu.is_connected:
            await lcu.run_auto_accept_loop()

if __name__ == "__main__":
    asyncio.run(main())