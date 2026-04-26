# ============================================================
# app.py ULTIMATE CHOROX + CHC + WALLET + SCAN
# Basado en tu app actual
# Mantiene:
# ✅ minería CHC
# ✅ explorer
# ✅ balances
# Agrega:
# ✅ wallet estilo Trust Wallet
# ✅ CHOROX BSC
# ✅ BNB balance
# ✅ sesión usuario
# ============================================================

import os
import json
import time
import hashlib
import secrets

from flask import (
    Flask, request, jsonify,
    render_template_string,
    redirect, session
)

from flask_cors import CORS
from pymongo import MongoClient, DESCENDING, ASCENDING

from web3 import Web3
from eth_account import Account
from eth_account.hdaccount import generate_mnemonic

# ============================================================
# APP
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "charly-super-key")
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# MONGO
# ============================================================

MONGO_URI = os.environ.get("MONGO_URI", "").strip()

if MONGO_URI == "":
    MONGO_URI = "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&tls=true"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client["charlycoin_db"]

collection = db["blockchain"]
wallets = db["wallets"]

collection.create_index("hash")
wallets.create_index("uid", unique=True)

try:
    collection.create_index([("indice", ASCENDING)], unique=True)
except:
    pass

# ============================================================
# CHC CONFIG
# ============================================================

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000
MAX_SUPPLY = 21000000000

ULTIMO_MINADO = {}

# ============================================================
# WEB3 BSC
# ============================================================

RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(RPC))

TOKEN_ADDRESS = Web3.to_checksum_address(
    "0x15681a8e9a8df14946a4f852822b709e37b70c4e"
)

TOKEN_ABI = [
{
 "constant":True,
 "inputs":[{"name":"owner","type":"address"}],
 "name":"balanceOf",
 "outputs":[{"name":"","type":"uint256"}],
 "type":"function"
},
{
 "constant":True,
 "inputs":[],
 "name":"decimals",
 "outputs":[{"name":"","type":"uint8"}],
 "type":"function"
}
]

token = w3.eth.contract(address=TOKEN_ADDRESS, abi=TOKEN_ABI)

# ============================================================
# HELPERS
# ============================================================

def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)
    texto = json.dumps(copia, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()

def crear_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": "0",
            "hash_anterior": "0"
        }
        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    return max(RECOMPENSA_INICIAL / (2 ** halvings), 0.00000001)

def create_wallet():
    mnemonic = generate_mnemonic(num_words=12, lang="english")
    acct = Account.from_mnemonic(mnemonic)
    return {
        "address": acct.address,
        "private_key": acct.key.hex(),
        "mnemonic": mnemonic
    }

def get_bnb(addr):
    try:
        wei = w3.eth.get_balance(addr)
        return round(float(w3.from_wei(wei, "ether")), 6)
    except:
        return 0

def get_chorox(addr):
    try:
        raw = token.functions.balanceOf(addr).call()
        dec = token.functions.decimals().call()
        return round(raw / (10 ** dec), 4)
    except:
        return 0

# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    html = """
    <html>
    <head>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <style>
    body{
        margin:0;
        font-family:Arial;
        background:#070b14;
        color:white;
        text-align:center;
    }
    .top{
        padding:40px;
        background:linear-gradient(135deg,#00bcd4,#2563eb);
        border-radius:0 0 30px 30px;
    }
    .btn{
        display:block;
        margin:15px;
        padding:16px;
        border-radius:14px;
        background:#111827;
        color:white;
        text-decoration:none;
        font-weight:bold;
    }
    </style>
    </head>
    <body>

    <div class='top'>
        <h1>🚀 CHOROX SUPER APP</h1>
        <p>Minería + Wallet + Explorer</p>
    </div>

    <a class='btn' href='/wallet'>💎 Wallet</a>
    <a class='btn' href='/scan'>⛓ Explorer</a>
    <a class='btn' href='/stats'>📊 Stats API</a>

    </body>
    </html>
    """
    return html

# ============================================================
# WALLET
# ============================================================

@app.route("/wallet")
def wallet():

    if "uid" not in session:

        uid = secrets.token_hex(8)
        data = create_wallet()

        wallets.insert_one({
            "uid": uid,
            **data
        })

        session["uid"] = uid

    row = wallets.find_one({"uid": session["uid"]})

    addr = row["address"]

    html = f"""
    <html>
    <body style='background:#111;color:white;font-family:Arial;padding:30px'>
    <h1>💎 Trust Wallet CHOROX</h1>

    <p><b>Wallet:</b><br>{addr}</p>

    <p>BNB: {get_bnb(addr)}</p>
    <p>CHOROX: {get_chorox(addr)}</p>

    <br>
    <a href='/seed' style='color:cyan'>🔑 Ver llave</a><br><br>
    <a href='/' style='color:lime'>🏠 Inicio</a>

    </body>
    </html>
    """

    return html
# ============================================================
# SEED
# ============================================================

@app.route("/seed")
def seed():

    if "uid" not in session:
        return "No wallet"

    row = wallets.find_one({"uid": session["uid"]})

    return f"<h2>{row['private']}</h2>"

# ============================================================
# SCAN
# ============================================================

@app.route("/scan")
def scan():

    chain = list(
        collection.find({}, {"_id":0})
        .sort("indice", DESCENDING)
        .limit(25)
    )

    rows = ""

    for b in chain:

        tx = b["transacciones"][0] if b["transacciones"] else {}

        rows += f"""
        <tr>
        <td>{b["indice"]}</td>
        <td>{tx.get("receptor","")[:20]}</td>
        <td>{tx.get("monto",0)}</td>
        </tr>
        """

    html = f"""
    <html>
    <body style='background:#000;color:white;font-family:Arial'>
    <h1>⛓ CHC Explorer</h1>
    <table border=1 cellpadding=8>
    <tr><th>Bloque</th><th>Wallet</th><th>Monto</th></tr>
    {rows}
    </table>
    <br><a href='/'>Inicio</a>
    </body>
    </html>
    """
    return html

# ============================================================
# API
# ============================================================

@app.route("/stats")
def stats():

    total = collection.count_documents({})

    pipeline = [
        {"$unwind":"$transacciones"},
        {"$group":{"_id":None,"total":{"$sum":"$transacciones.monto"}}}
    ]

    result = list(collection.aggregate(pipeline))
    supply = result[0]["total"] if result else 0

    return jsonify({
        "bloques": max(total-1,0),
        "supply": round(supply,2),
        "reward": recompensa_actual()
    })

# ============================================================
# BALANCE CHC
# ============================================================

def balance_calc(wallet):

    pipeline = [
        {"$unwind":"$transacciones"},
        {"$match":{"transacciones.receptor":wallet}},
        {"$group":{"_id":None,"total":{"$sum":"$transacciones.monto"}}}
    ]

    res = list(collection.aggregate(pipeline))
    return round(res[0]["total"],2) if res else 0

@app.route("/balance/<wallet>")
def balance(wallet):
    return jsonify({
        "wallet": wallet,
        "balance": balance_calc(wallet)
    })

# ============================================================
# MINAR
# ============================================================

@app.route("/minar", methods=["POST"])
def minar():

    data = request.get_json(force=True)

    wallet = str(data.get("wallet","")).strip()
    nonce = str(data.get("nonce","")).strip()

    if not wallet or not nonce:
        return jsonify({"error":"faltan datos"}),400

    ahora = time.time()

    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < 2:
            return jsonify({"error":"espera"}),429

    prueba = hashlib.sha256(
        f"{wallet}{nonce}".encode()
    ).hexdigest()

    if not prueba.startswith("0"*DIFICULTAD):
        return jsonify({"error":"hash invalido"}),400

    ultimo = collection.find_one(sort=[("indice",-1)])

    nuevo = {
        "indice": ultimo["indice"]+1,
        "timestamp": ahora,
        "transacciones":[{
            "emisor":"RED",
            "receptor":wallet,
            "monto":recompensa_actual()
        }],
        "nonce":nonce,
        "hash_anterior":ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)

    collection.insert_one(nuevo)

    ULTIMO_MINADO[wallet] = ahora

    return jsonify({
        "ok":True,
        "bloque":nuevo["indice"]
    })

# ============================================================
# START
# ============================================================

@app.route("/test")
def test():
    return "ok"
from flask import session
import secrets
from web3 import Web3
from eth_account import Account

app.secret_key = "charly_super_wallet"

# BSC
RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(RPC))

CHOROX = Web3.to_checksum_address("0x15681a8e9a8df14946a4f852822b709e37b70c4e")

ABI = [
 {
   "constant":True,
   "inputs":[{"name":"owner","type":"address"}],
   "name":"balanceOf",
   "outputs":[{"name":"","type":"uint256"}],
   "type":"function"
 }
]

token = w3.eth.contract(address=CHOROX, abi=ABI)

# Mongo
wallets = db["wallets"]

def create_wallet():
    acct = Account.create()
    return {
        "address": acct.address,
        "private": acct.key.hex()
    }

def get_bnb(addr):
    try:
        bal = w3.eth.get_balance(addr)
        return round(w3.from_wei(bal,"ether"),6)
    except:
        return 0

def get_chorox(addr):
    try:
        bal = token.functions.balanceOf(addr).call()
        return round(bal / 10**18,4)
    except:
        return 0
if __name__ == "__main__":
    crear_genesis()
    app.run(host="0.0.0.0", port=PORT)
