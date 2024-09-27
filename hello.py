from typing import List
from flask import Flask, jsonify
from solders.pubkey import Pubkey
import csv, json, os
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
SQUADS_DUNE_QUERY_ID = 4105938
def load_squads_map():
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
    if os.path.exists(LATEST_SQUADS_CSV):
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
    return squads_map

if os.path.exists(LATEST_SQUADS_MAP_JSON):
    with open(LATEST_SQUADS_MAP_JSON, "r") as f:
        squads_map = json.load(f)
else:
    squads_map = load_squads_map()

app = Flask(__name__)


@app.route("/")
def main():
    return "Hello from squads-reverse-map-api!"


@app.route("/squads/<squad_id>")
def squad_by_id(squad_id):
    if squad_id in squads_map:
        return jsonify(squads_map[squad_id]), 200
    else:
        return jsonify({"error": "Squad not found"}), 404