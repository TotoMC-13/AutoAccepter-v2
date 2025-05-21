import requests
import os
import platform
import json
import time

LCU_READY_CHECK_ENDPOINT = "/lol-matchmaking/v1/ready-check"
LCU_ACCEPT_ENDPOINT = "/lol-matchmaking/v1/ready-check/accept"
LCU_GAMEFLOW_STATE_ENDPOINT = "/lol-gameflow/v1/gameflow-phase"

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def get_default_lol_lockfile_path():
    system = platform.system()
    if system == "Windows":
        lol_path = r"D:\Riot Games\League of Legends\lockfile"
        if os.path.exists(lol_path):
            return lol_path
        
        print("Lockfile no encontrado en D:\\Riot Games\\League of Legends\\lockfile.")
        return None
    
def read_lol_lockfile_data(lockfile_path=None):
    if lockfile_path is None:
        lockfile_path = get_default_lol_lockfile_path()
    if not lockfile_path or not os.path.exists(lockfile_path):
        return None
    try:
        with open(lockfile_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        parts = content.split(':')
        if len(parts) == 5:
            return {
                "process_name": parts[0], "process_id": int(parts[1]),
                "port": int(parts[2]), "password": parts[3], "protocol": parts[4]
            }
        return None
    except (IOError, ValueError):
        return None
    
print(f"\n{read_lol_lockfile_data()}") # Ej: {'process_name': 'LeagueClient', 'process_id': 17968, 'port': 51308, 'password': 'mQr8OsqYuL-CP3DVr1msrQ', 'protocol': 'https'}

def get_lcu_connection():
    lockfile_data = read_lol_lockfile_data()

    protocol = lockfile_data['protocol']
    port = lockfile_data['port']
    password = lockfile_data['password']
    
    base_url = f"{protocol}://127.0.0.1:{port}"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    return base_url, headers, password

def make_request(endpoint):
    base_url, headers, password_lcu = get_lcu_connection()
    url_completa = f"{base_url}{endpoint}"

    response = requests.get(url_completa, auth=('riot', password_lcu), headers=headers, verify=False, timeout=5)

    # For debugging
    # formatted_json = json.dumps(response.json(), indent=2, ensure_ascii=False)

    # print(f"\n{formatted_json}")

    return response, response.json()

while True:
    response, json_data = make_request(LCU_READY_CHECK_ENDPOINT)
    _, gameflow = make_request(LCU_GAMEFLOW_STATE_ENDPOINT)

    if gameflow == 'Lobby':
        print("Esperando en el lobby.")

    if response.status_code == 200 and json_data.get("state") == "InProgress":
        base_url, headers, password_lcu = get_lcu_connection()
        accept_url = f"{base_url}{LCU_ACCEPT_ENDPOINT}"
        requests.post(accept_url, auth=('riot', password_lcu), headers=headers, verify=False, timeout=5)
        print("Partida aceptada.")

    time.sleep(3)
