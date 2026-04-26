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
    <title>CHOROX Super App</title>

    <style>
    *{
        margin:0;
        padding:0;
        box-sizing:border-box;
    }

    body{
        font-family:Arial,Helvetica,sans-serif;
        background:#050816;
        color:white;
        min-height:100vh;
    }

    .hero{
        padding:55px 25px 45px 25px;
        background:
        radial-gradient(circle at top right,#1d4ed8 0%,transparent 35%),
        radial-gradient(circle at top left,#06b6d4 0%,transparent 35%),
        linear-gradient(135deg,#0f172a,#111827,#0b1020);
        border-radius:0 0 35px 35px;
        box-shadow:0 10px 30px rgba(0,0,0,.45);
    }

    .badge{
        display:inline-block;
        padding:8px 14px;
        border-radius:30px;
        background:rgba(255,255,255,.08);
        font-size:12px;
        letter-spacing:1px;
        margin-bottom:18px;
        border:1px solid rgba(255,255,255,.08);
    }

    h1{
        font-size:34px;
        font-weight:900;
        letter-spacing:.5px;
        margin-bottom:10px;
    }

    .sub{
        color:#cbd5e1;
        font-size:15px;
        line-height:1.6;
        max-width:500px;
        margin:auto;
    }

    .wrap{
        padding:22px;
        max-width:650px;
        margin:auto;
    }

    .card{
        background:#0f172a;
        border:1px solid #1e293b;
        border-radius:22px;
        padding:18px;
        margin-bottom:18px;
        box-shadow:0 8px 24px rgba(0,0,0,.25);
    }

    .row{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:14px;
        margin-top:14px;
    }

    .btn{
        display:block;
        text-decoration:none;
        color:white;
        font-weight:700;
        padding:18px;
        border-radius:18px;
        margin-bottom:14px;
        transition:.2s;
    }

    .btn:active{
        transform:scale(.98);
    }

    .wallet{
        background:linear-gradient(135deg,#2563eb,#1d4ed8);
    }

    .scan{
        background:linear-gradient(135deg,#10b981,#059669);
    }

    .stats{
        background:linear-gradient(135deg,#7c3aed,#6d28d9);
    }

    .mine{
        background:linear-gradient(135deg,#f59e0b,#d97706);
    }

    .mini{
        background:#111827;
        border:1px solid #1f2937;
        border-radius:18px;
        padding:16px;
        text-align:left;
    }

    .mini small{
        color:#94a3b8;
        display:block;
        margin-bottom:8px;
    }

    .mini b{
        font-size:18px;
    }

    .footer{
        text-align:center;
        color:#64748b;
        font-size:12px;
        padding:20px 0 35px;
    }
    </style>
    </head>

    <body>

    <div class='hero'>
        <div class='badge'>CHC • WEB3 • BNB CHAIN • CHOROX</div>
        <h1>💎 CHC SUPER APP- CHARLYCOIN</h1>
        <div class='sub'>
            Wallet descentralizada, explorer en vivo,
            minería CHC y herramientas Web3 en una sola app.
        </div>
    </div>

    <div class='wrap'>

        <div class='card'>
            <a class='btn wallet' href='/wallet'>💼 Abrir Wallet</a>
            <a class='btn scan' href='/scan'>⛓ Blockchain Explorer</a>
            <a class='btn stats' href='/stats'>📊 Estadísticas</a>
            <a class='btn mine' href='/cadena'>🚀 Últimos Bloques</a>
        </div>

        <div class='row'>
            <div class='mini'>
                <small>Token Principal</small>
                <b>CHOROX</b>
            </div>

            <div class='mini'>
                <small>Red</small>
                <b>BNB Smart Chain</b>
            </div>

            <div class='mini'>
                <small>Minería</small>
                <b>CHC Network</b>
            </div>

            <div class='mini'>
                <small>Estado</small>
                <b style='color:#22c55e;'>● Online</b>
            </div>
        </div>

        <div class='footer'>
            Powered by Charly Network • Trust Style UI
        </div>

    </div>

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
    <a href="/backup">📥 Descargar Backup</a>
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
# stats
# ============================================================
@app.route("/stats")
def stats():
    total = collection.count_documents({})

    pipeline = [
        {"$unwind": "$transacciones"},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]

    result = list(collection.aggregate(pipeline))
    supply = result[0]["total"] if result else 0

    reward = recompensa_actual()

    return jsonify({
        "bloques": max(total - 1, 0),
        "supply": round(float(supply), 2),
        "recompensa": float(reward),
        "dificultad": DIFICULTAD
    })

# ============================================================
# SCAN
# ============================================================

# ============================================================
# SCAN PROFESIONAL (REEMPLAZA SOLO TU RUTA /scan)
# NO TOCA /minar /cadena /stats /balance
# LOS MINEROS SIGUEN FUNCIONANDO IGUAL
# ============================================================

@app.route("/scan")
def scan():

    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CharlyScan PRO</title>

<style>
*{
margin:0;
padding:0;
box-sizing:border-box;
}

body{
font-family:Arial,Helvetica,sans-serif;
background:#070b14;
color:white;
padding:18px;
}

.wrap{
max-width:1300px;
margin:auto;
}

.top{
background:linear-gradient(135deg,#06b6d4,#2563eb,#1d4ed8);
padding:30px;
border-radius:24px;
margin-bottom:20px;
box-shadow:0 12px 35px rgba(0,0,0,.35);
}

.top h1{
font-size:38px;
font-weight:900;
}

.top p{
opacity:.92;
margin-top:8px;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
gap:15px;
margin-bottom:20px;
}

.card{
background:#111827;
border:1px solid #1f2937;
border-radius:18px;
padding:18px;
box-shadow:0 8px 24px rgba(0,0,0,.22);
}

.card small{
display:block;
color:#94a3b8;
margin-bottom:8px;
font-size:12px;
text-transform:uppercase;
letter-spacing:1px;
}

.big{
font-size:28px;
font-weight:900;
}

.green{color:#22c55e;}
.yellow{color:#facc15;}
.cyan{color:#22d3ee;}
.purple{color:#c084fc;}

.search{
display:flex;
gap:10px;
margin-bottom:20px;
flex-wrap:wrap;
}

.search input{
flex:1;
min-width:250px;
padding:15px;
border:none;
outline:none;
border-radius:14px;
background:#111827;
color:#22d3ee;
font-size:15px;
}

.search button{
padding:15px 22px;
border:none;
border-radius:14px;
background:#2563eb;
color:white;
font-weight:700;
cursor:pointer;
}

.tablebox{
background:#111827;
border:1px solid #1f2937;
border-radius:18px;
overflow:hidden;
}

.tabletitle{
padding:16px;
font-weight:800;
border-bottom:1px solid #1f2937;
}

.tablewrap{
overflow-x:auto;
}

table{
width:100%;
border-collapse:collapse;
min-width:850px;
}

th{
padding:14px;
text-align:left;
font-size:12px;
color:#94a3b8;
background:#0b1220;
}

td{
padding:14px;
border-top:1px solid #1f2937;
font-size:14px;
}

tr:hover{
background:#0f172a;
}

.hash{
font-family:monospace;
font-size:12px;
color:#64748b;
}

.addr{
font-family:monospace;
font-size:12px;
color:#cbd5e1;
}

.badge{
padding:5px 10px;
border-radius:30px;
background:#052e16;
color:#22c55e;
font-size:12px;
display:inline-block;
}

.footer{
text-align:center;
padding:25px;
color:#64748b;
font-size:12px;
}

@media(max-width:700px){
.top h1{font-size:28px;}
.big{font-size:24px;}
}
</style>
</head>

<body>

<div class="wrap">

<div class="top">
<h1>⛓ CHARLYSCAN PRO</h1>
<p>Blockchain Explorer • Minería CHC en tiempo real</p>
</div>

<div class="grid">

<div class="card">
<small>Estado Nodo</small>
<div class="big green">● ONLINE</div>
</div>

<div class="card">
<small>Bloques</small>
<div class="big cyan" id="blocks">0</div>
</div>

<div class="card">
<small>Supply</small>
<div class="big yellow" id="supply">0 CHC</div>
</div>

<div class="card">
<small>Reward</small>
<div class="big purple" id="reward">0</div>
</div>

</div>

<div class="card" style="margin-bottom:20px;">
<small>Wallet Tracker</small>

<div class="search">
<input id="wallet" placeholder="Pega wallet pública CHC...">
<button onclick="buscar()">Buscar</button>
</div>

<div class="big yellow" id="saldo">0 CHC</div>
</div>

<div class="tablebox">

<div class="tabletitle">
Últimos Bloques Minados
</div>

<div class="tablewrap">
<table>
<thead>
<tr>
<th>Bloque</th>
<th>Minero</th>
<th>Reward</th>
<th>Hash</th>
</tr>
</thead>

<tbody id="blockchain-table"></tbody>

</table>
</div>

</div>

<div class="footer">
Powered by Charly Network • Mining Explorer
</div>

</div>

<script>

async function cargar(){

try{

const [a,b] = await Promise.all([
fetch('/cadena'),
fetch('/stats')
])

const chain = await a.json()
const stats = await b.json()

document.getElementById("blocks").innerText =
Number(stats.bloques || 0).toLocaleString();

document.getElementById("supply").innerText =
Number(stats.supply || 0).toLocaleString() + " CHC";

document.getElementById("last-reward").innerText =
Number(stats.recompensa || 0).toFixed(8) + " CHC";

let html = ""

let tableHtml = "";

chain.forEach(block => {

    if (!block.transacciones) return;
    if (block.transacciones.length === 0) return;

    let tx = block.transacciones[0];

    tableHtml += `
    <tr>
        <td class='cyan'>#${block.indice}</td>

        <td class='addr'>
            ${String(tx.receptor).substring(0,26)}...
        </td>

        <td class='yellow'>
            +${Number(tx.monto).toLocaleString()}
        </td>

        <td class='hash'>
            ${String(block.hash).substring(0,28)}...
        </td>
    </tr>
    `;
});

document.getElementById("blockchain-table").innerHTML = tableHtml;
document.getElementById("tabla").innerHTML = html

}catch(e){
console.log(e)
}

}

async function buscar(){

let w = document.getElementById("wallet").value.trim()

if(!w) return

try{

let r = await fetch("/balance/" + w)
let j = await r.json()

document.getElementById("saldo").innerText =
Number(j.balance).toLocaleString(undefined,{minimumFractionDigits:2}) + " CHC"

}catch(e){}

}

setInterval(cargar,10000)
cargar()

</script>

</body>
</html>
"""
    return html



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
# backup
# ============================================================
@app.route("/backup")
def backup():

    if "uid" not in session:
        return "No wallet"

    row = wallets.find_one({"uid": session["uid"]})

    data = {
        "address": row["address"],
        "seed": row.get("seed",""),
        "private_key": row.get("private","")
    }

    mem = io.BytesIO()
    mem.write(json.dumps(data, indent=4).encode())
    mem.seek(0)

    return send_file(
        mem,
        as_attachment=True,
        download_name="chorox_wallet_backup.json",
        mimetype="application/json"
    )

# ============================================================
# cadena
# ============================================================

@app.route("/cadena")
def cadena():
    datos = list(
        collection.find({}, {"_id": 0})
        .sort("indice", DESCENDING)
        .limit(50)
    )
    return jsonify(datos)

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
from flask import send_file
import json, io

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
