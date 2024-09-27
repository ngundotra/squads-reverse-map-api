from typing import List
import csv, json, os
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify
from solders.pubkey import Pubkey
import requests

SQUADS_V3 = Pubkey.from_string("SMPLecH534NA9acpos4G6x7uf3LWbCAwZQE9e8ZekMu")
SQUADS_V4 = Pubkey.from_string('SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf')

def find_v3_vault(multisig: Pubkey, index=1):
    # v4 program vaults start by default with index 1
    return Pubkey.find_program_address([
        bytes(b"squad"),
        bytes(multisig),
        index.to_bytes(4, byteorder="little"), # note authority index is an u32 (4 byte)
        bytes(b"authority"),
    ], SQUADS_V3)[0]

def find_v4_vault(multisig: Pubkey, index=0):
    # v4 program vaults start by default with index 0
    return Pubkey.find_program_address([
        bytes(b'multisig'),
        bytes(multisig),
        bytes(b'vault'),
        bytes([index]), # u8
    ], SQUADS_V4)[0]

def find_vault(squad_type: str, multisig: Pubkey, **kwargs):
    if squad_type == 'v4':
        return find_v4_vault(multisig, **kwargs)
    elif squad_type == 'v3':
        return find_v3_vault(multisig, **kwargs)
    raise ValueError(f"Unknown squad type: {squad_type}")


LATEST_SQUADS_CSV = "latest-squads.csv"
LATEST_SQUADS_MAP_JSON = "squads-map.json"
# Visible at: https://dune.com/queries/4105938
SQUADS_DUNE_QUERY_ID = 4105938

def load_squads_map(force_load=False):
    global SQUADS_MAP
    print("Loading squads map...")
    def derive_vaults(csv_data: List[str], MAX_DERIVED_VAULTS=10):
        for i, row in enumerate(csv.reader(csv_data)):
            if i == 0: # skip header
                continue 
            squad_type, multisig = row
            for i in range(MAX_DERIVED_VAULTS):
                vault = find_vault(squad_type, Pubkey.from_string(multisig), index=i)
                squads_map[str(vault)] = { "multisig": multisig, "squad_type": squad_type }
        return squads_map

    squads_map = {}
    if not force_load and os.path.exists(LATEST_SQUADS_CSV):
        with open(LATEST_SQUADS_CSV, "r") as f:
            squads_map = derive_vaults(f.readlines())
    else:
        response = requests.get(f"https://api.dune.com/api/v1/query/{SQUADS_DUNE_QUERY_ID}/results/csv", headers={"X-DUNE-API-KEY": os.getenv("DUNE_API_KEY")})
        if response.status_code == 200:
            with open(LATEST_SQUADS_CSV, "w") as f:
                f.write(response.text)
            squads_map = derive_vaults(response.text.splitlines())
        else:
            print(f"Failed to load squads map: {response.status_code}")
            raise Exception(f"Failed to load squads map: {response.status_code}")

    with open(LATEST_SQUADS_MAP_JSON, "w") as f:
        json.dump(squads_map, f)

    SQUADS_MAP = squads_map

SQUADS_MAP = {}
if os.path.exists(LATEST_SQUADS_MAP_JSON):
    print("Loading squads map from cache...")
    with open(LATEST_SQUADS_MAP_JSON, "r") as f:
        SQUADS_MAP = json.load(f)
else:
    load_squads_map()

scheduler = BackgroundScheduler(daemon=True)
# Force load the squads CSV on startup and then every 24 hours
scheduler.add_job(
    lambda: load_squads_map(force_load=True), 
    'interval', 
    hours=24, 
    next_run_time=datetime.datetime.now() + datetime.timedelta(hours=24)
)
scheduler.start()

app = Flask(__name__)

@app.route("/")
def main():
    return "Hello from squads-reverse-map-api!"


@app.route("/squad/<vault_address>")
def squad_by_vault(vault_address):
    if vault_address in SQUADS_MAP:
        return jsonify(SQUADS_MAP[vault_address]), 200
    else:
        return jsonify({"error": "Squad not found"}), 404