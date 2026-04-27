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
import unicodedata
from pymongo import MongoClient
from web3 import Web3
import os

BSC_RPC = "https://bsc-dataseed.binance.org/"

w3 = Web3(Web3.HTTPProvider(BSC_RPC))

TOKEN_ADDRESS = Web3.to_checksum_address("0x15681A8E9a8dF14946A4F852822B709e37b70c4E")
OWNER = Web3.to_checksum_address("0xd4508db1aDC48deA121f356B254a7155DDAB36Ae")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

def send_chorox(to, amount):

    to = Web3.to_checksum_address(to)

    contract = w3.eth.contract(
        address=TOKEN_ADDRESS,
        abi=ABI
    )

    decimals = 18
    value = int(amount * (10 ** decimals))

    nonce = w3.eth.get_transaction_count(OWNER)

    tx = contract.functions.transfer(
        to,
        value
    ).build_transaction({
        "chainId": 56,
        "gas": 120000,
        "gasPrice": w3.to_wei("3", "gwei"),
        "nonce": nonce
    })

    signed = w3.eth.account.sign_transaction(
        tx,
        PRIVATE_KEY
    )

    tx_hash = w3.eth.send_raw_transaction(
        signed.raw_transaction
    )

    return tx_hash.hex()
 # ============================================================
# FINs
# ============================================================  

ABI = [{
    "constant": False,
    "inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_value", "type": "uint256"}
    ],
    "name": "transfer",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function"
}]

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)



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



app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "charly-super-key")
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# claim_bonus
# ============================================================
from datetime import datetime, timedelta
from pymongo import MongoClient
client = MongoClient(MONGO_URI)
db = client["charlycoin"]
claims = db["bonus_claims"]

bonus_memory = {}



@app.route("/claim_bonus", methods=["POST"])
def claim_bonus():

    wallet = request.form["wallet"].strip().lower()
    now = datetime.utcnow()

    row = claims.find_one({"wallet": wallet})

    if row:
        last = row["last_claim"]
        next_time = last + timedelta(hours=24)

        if now < next_time:
            faltan = next_time - now
            horas = int(faltan.total_seconds() // 3600)
            minutos = int((faltan.total_seconds() % 3600) // 60)
            return f"⏳ Espera {horas}h {minutos}m"

    # Validar minería
    mined = True

    if not mined:
        return "❌ No minaste en últimas 24h"

    # Enviar premio
    # send_chorox(wallet, 100)

    claims.update_one(
        {"wallet": wallet},
        {"$set": {"last_claim": now}},
        upsert=True
    )

    return "✅ 100 CHOROX enviados"
    
    # =========================
    # Validar si minó CHC hoy
    # =========================
    mined = True

    if not mined:
        return "❌ No minaste en últimas 24h"

    # =========================
    # Enviar 100 CHOROX
    # =========================
   # enviar token real
    send_chorox(wallet, 100)

    claims.update_one(
        {"wallet": wallet},
        {"$set": {"last_claim": now}},
        upsert=True
    )

return "✅ 100 CHOROX enviados"

    # ==========================
    # AQUÍ validas si minó CHC
    # ==========================
   
       
    # ==========================
    # AQUÍ envías CHOROX real
    # ==========================
    # send_chorox(wallet, 100)

    bonus_memory[wallet] = now + timedelta(hours=24)

    return "✅ 100 CHOROX enviados"

# ============================================================
# chc_available
# ============================================================
def chc_available(uid):

    row = wallets.find_one({"uid": uid})
    addr = row["address"]

    pipeline = [
        {"$unwind":"$transacciones"},
        {"$match":{"transacciones.receptor":addr}},
        {"$group":{"_id":None,"total":{"$sum":"$transacciones.monto"}}}
    ]

    res = list(collection.aggregate(pipeline))

    mined = res[0]["total"] if res else 0

    swapped = row.get("chc_swapped",0)

    return mined - swapped


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
# swap
# ============================================================



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
<!DOCTYPE html>
<html>
<head>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>CHC CHARLYCOIN Super App</title>

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
    margin-bottom:10px;
}

.sub{
    color:#cbd5e1;
    font-size:15px;
    line-height:1.6;
    max-width:560px;
}

.wrap{
    max-width:1180px;
    margin:auto;
    padding:24px;
}

.grid{
    display:grid;
    grid-template-columns: 1.2fr .8fr;
    gap:24px;
}

.card{
    background:#0f172a;
    border:1px solid #1e293b;
    border-radius:22px;
    padding:18px;
    box-shadow:0 8px 24px rgba(0,0,0,.25);
}

.btn{
    display:block;
    text-decoration:none;
    color:white;
    font-weight:700;
    padding:18px;
    border-radius:18px;
    margin-bottom:14px;
}

.wallet{background:linear-gradient(135deg,#2563eb,#1d4ed8);}
.scan{background:linear-gradient(135deg,#10b981,#059669);}
.stats{background:linear-gradient(135deg,#7c3aed,#6d28d9);}
.mine{background:linear-gradient(135deg,#f59e0b,#d97706);}
.trade{background:linear-gradient(135deg,#ec4899,#db2777);}
.swap{background:linear-gradient(135deg,#06b6d4,#0891b2);}
.market{background:linear-gradient(135deg,#ef4444,#dc2626);}

.side{
    background:#0f172a;
    border:1px solid #1e293b;
    border-radius:22px;
    padding:20px;
    box-shadow:0 8px 24px rgba(0,0,0,.25);
    height:fit-content;
}

.side h2{
    font-size:24px;
    margin-bottom:12px;
}

.reward{
    font-size:48px;
    font-weight:900;
    color:#22c55e;
    margin:12px 0;
}

.input{
    width:100%;
    padding:14px;
    border-radius:14px;
    border:none;
    outline:none;
    background:#111827;
    color:white;
    margin-top:10px;
}

.claim{
    width:100%;
    border:none;
    padding:16px;
    border-radius:16px;
    margin-top:14px;
    font-size:18px;
    font-weight:900;
    color:white;
    cursor:pointer;
    background:linear-gradient(135deg,#22c55e,#16a34a);
}

.claim:disabled{
    opacity:.5;
    cursor:not-allowed;
}

.small{
    color:#94a3b8;
    font-size:13px;
    margin-top:10px;
    line-height:1.5;
}

.timer{
    margin-top:14px;
    font-size:18px;
    font-weight:700;
    color:#f59e0b;
}

.status{
    margin-top:12px;
    font-size:14px;
    color:#22c55e;
}

.row{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:14px;
    margin-top:18px;
}

.mini{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:18px;
    padding:16px;
}

.mini small{
    color:#94a3b8;
    display:block;
    margin-bottom:8px;
}

.footer{
    text-align:center;
    color:#64748b;
    font-size:12px;
    padding:25px 0 10px;
}

@media(max-width:900px){
    .grid{
        grid-template-columns:1fr;
    }
}
</style>
</head>

<body>

<div class='hero'>
    <div class='badge'>CHC • WEB3 • BONUS DIARIO</div>
    <h1>💎 CHC SUPER APP - CHARLYCOIN</h1>
    <div class='sub'>
        Wallet descentralizada, explorer en vivo, minería CHC,
        swap y ahora recompensas diarias en CHOROX.
    </div>
</div>

<div class='wrap'>

<div class='grid'>

<div class='card'>
    <a class='btn wallet' href='/wallet'>💼 Abrir Wallet</a>
    <a class='btn scan' href='/scan'>⛓ Blockchain Explorer</a>
    <a class='btn stats' href='/stats'>📊 Estadísticas</a>
    <a class='btn mine' href='/cadena'>🚀 Últimos Bloques</a>
    <a class='btn trade' href='/trade'>📈 Comprar Criptos</a>
    <a class='btn swap' href='/swap'>🔄 Swap CHC ↔ CHOROX</a>
    <a class='btn market' href='/prices'>🔥 Mercado Binance</a>

    <div class='row'>
        <div class='mini'>
            <small>Token</small>
            <b>CHOROX</b>
        </div>

        <div class='mini'>
            <small>Red</small>
            <b>BSC</b>
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
</div>

<div class='side'>

    <h2>🎁 Bonus Diario</h2>

    <div class='small'>
        Si minaste CHC en las últimas 24 horas puedes reclamar:
    </div>

    <div class='reward'>100 CHOROX</div>

    <input id='wallet' class='input'
    placeholder='Pega tu wallet BSC / minera'>

    <button id='btn' class='claim' onclick='claimNow()'>
        Reclamar Ahora
    </button>

    <div class='timer' id='timer'>
        Disponible ahora
    </div>

    <div class='status' id='msg'></div>

    <div class='small'>
        El sistema guarda tu dirección y solo permite un reclamo cada 24 horas.
        Debes haber minado CHC recientemente.
    </div>

</div>

</div>

<div class='footer'>
Powered by Charly Network • Trust Style UI
</div>

</div>

<script>

let saved = localStorage.getItem("wallet_chc");
if(saved){
    document.getElementById("wallet").value = saved;
}

async function claimNow(){

    let wallet = document.getElementById("wallet").value.trim();

    if(!wallet){
        alert("Pon tu wallet");
        return;
    }

    localStorage.setItem("wallet_chc", wallet);

    document.getElementById("msg").innerHTML = "Procesando...";
    document.getElementById("btn").disabled = true;

    let fd = new FormData();
    fd.append("wallet", wallet);

    let r = await fetch("/claim_bonus",{
        method:"POST",
        body:fd
    });

    let t = await r.text();

    document.getElementById("msg").innerHTML = t;

    if(t.includes("✅")){
        startTimer(86400);
    }else{
        document.getElementById("btn").disabled = false;
    }
}

function startTimer(sec){

    let box = document.getElementById("timer");

    let x = setInterval(()=>{

        sec--;

        let h = Math.floor(sec/3600);
        let m = Math.floor((sec%3600)/60);
        let s = sec%60;

        box.innerHTML =
        h+"h "+m+"m "+s+"s";

        if(sec<=0){
            clearInterval(x);
            box.innerHTML = "Disponible ahora";
            document.getElementById("btn").disabled = false;
        }

    },1000);
}

</script>

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
# getenv
# ============================================================



API_KEY = os.getenv("BINANCE_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET")

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

    bloques = max(total - 1, 0)

    halvings = bloques // HALVING_CADA
    reward = RECOMPENSA_INICIAL / (2 ** halvings)

    if reward < 0.00000001:
        reward = 0.00000001

    return jsonify({
        "bloques": bloques,
        "supply": round(float(supply), 2),
        "recompensa": reward,
        "dificultad": DIFICULTAD
    })

# ============================================================
# SCAN
# ============================================================

@app.route("/scan")
def scan():

    html = """
<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>CharlyScan PRO</title>

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
padding:22px;
}

.wrap{
max-width:1400px;
margin:auto;
}

.top{
background:linear-gradient(135deg,#00c6ff,#1d4ed8,#312e81);
padding:38px;
border-radius:28px;
box-shadow:0 20px 50px rgba(0,0,0,.35);
margin-bottom:22px;
}

.logo{
font-size:46px;
font-weight:900;
letter-spacing:2px;
}

.sub{
margin-top:10px;
font-size:18px;
opacity:.9;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
gap:18px;
margin-bottom:22px;
}

.card{
background:#091224;
border:1px solid #162544;
border-radius:22px;
padding:24px;
box-shadow:0 10px 30px rgba(0,0,0,.25);
}

.label{
font-size:13px;
color:#93a4c7;
letter-spacing:2px;
text-transform:uppercase;
margin-bottom:14px;
}

.big{
font-size:42px;
font-weight:900;
}

.green{color:#22c55e;}
.cyan{color:#22d3ee;}
.yellow{color:#facc15;}
.purple{color:#c084fc;}

.wallet{
background:#091224;
border:1px solid #162544;
border-radius:24px;
padding:25px;
margin-bottom:22px;
}

.row{
display:flex;
gap:15px;
flex-wrap:wrap;
}

input{
flex:1;
min-width:260px;
padding:18px;
background:#030712;
border:1px solid #1e293b;
color:white;
border-radius:16px;
font-size:16px;
}

button{
padding:18px 34px;
border:none;
border-radius:16px;
font-weight:800;
cursor:pointer;
background:linear-gradient(135deg,#2563eb,#1d4ed8);
color:white;
font-size:16px;
}

button:hover{
transform:scale(1.03);
}

.balance{
margin-top:18px;
font-size:40px;
font-weight:900;
color:#facc15;
}

.panel{
background:#091224;
border:1px solid #162544;
border-radius:24px;
overflow:hidden;
}

.head{
padding:22px;
font-size:28px;
font-weight:900;
border-bottom:1px solid #162544;
display:flex;
justify-content:space-between;
flex-wrap:wrap;
gap:10px;
}

a{
color:#22d3ee;
text-decoration:none;
font-weight:700;
}

a:hover{
color:white;
}

table{
width:100%;
border-collapse:collapse;
}

th{
text-align:left;
padding:18px;
color:#8ea2c9;
font-size:13px;
text-transform:uppercase;
letter-spacing:1px;
background:#08101d;
}

td{
padding:18px;
border-top:1px solid #13203d;
font-size:15px;
}

tr:hover{
background:#0d1830;
}

.hash{
font-size:12px;
color:#7b8cae;
}

.addr{
font-size:13px;
color:#d1d5db;
}

.footer{
margin-top:20px;
text-align:center;
color:#6b7280;
font-size:13px;
}

@media(max-width:700px){
.logo{font-size:32px;}
.big{font-size:28px;}
.head{font-size:22px;}
}
</style>
</head>

<body>
<div class='wrap'>

<div class='top'>
<div class='logo'>⛓ CHARLYSCAN PRO</div>
<div class='sub'>Blockchain Explorer • Minería CHC • Wallet Tracker Profesional</div>
</div>

<div class='grid'>

<div class='card'>
<div class='label'>Estado Nodo</div>
<div class='big green'>● ONLINE</div>
</div>

<div class='card'>
<div class='label'>Bloques</div>
<div class='big cyan' id='blocks'>0</div>
</div>

<div class='card'>
<div class='label'>Supply</div>
<div class='big yellow' id='supply'>0 CHC</div>
</div>

<div class='card'>
<div class='label'>
Reward •
<a target='_blank' href='/stats'>ver stats</a>
</div>
<div class='big purple' id='last-reward'>LIVE</div>
</div>

</div>

<div class='wallet'>
<div class='label'>Wallet Tracker</div>

<div class='row'>
<input id='wallet-input' placeholder='Pega wallet pública CHC...'>

<button onclick='buscarWallet()'>Buscar</button>
</div>

<div class='balance' id='user-balance'>0 CHC</div>
</div>

<div class='panel'>
<div class='head'>
<span>Últimos Bloques Minados</span>
<a target='_blank' href='/cadena'>Abrir JSON cadena</a>
</div>

<table>
<thead>
<tr>
<th>Bloque</th>
<th>Minero</th>
<th>Reward</th>
<th>Hash</th>
</tr>
</thead>

<tbody id='blockchain-table'></tbody>

</table>
</div>

<div class='footer'>
CHOROX • CHC • CharlyScan Professional Edition
</div>

</div>

<script>

async function cargar(){

let stats = await fetch('/stats').then(r=>r.json());
let chain = await fetch('/cadena').then(r=>r.json());

document.getElementById("blocks").innerText =
Number(stats.bloques).toLocaleString("es-MX");

document.getElementById("supply").innerText =
Number(stats.supply).toLocaleString("es-MX") + " CHC";

document.getElementById("last-reward").innerHTML =
"<a target='_blank' href='/stats'>" +
Number(stats.recompensa).toLocaleString("es-MX") +
" CHC</a>";

let html = "";

chain.forEach(x=>{

let tx = x.transacciones?.[0];
if(!tx) return;

html += `
<tr>
<td class='cyan'>#${x.indice}</td>
<td class='addr'>${String(tx.receptor).substring(0,22)}...</td>
<td class='yellow'>+${Number(tx.monto).toLocaleString("es-MX")}</td>
<td class='hash'>${String(x.hash).substring(0,28)}...</td>
</tr>
`;

});

document.getElementById("blockchain-table").innerHTML = html;

}

async function buscarWallet(){

let w = document.getElementById("wallet-input").value.trim();

if(!w) return;

let data = await fetch("/balance/"+w).then(r=>r.json());

document.getElementById("user-balance").innerText =
Number(data.balance).toLocaleString("es-MX") + " CHC";

}

cargar();
setInterval(cargar,10000);

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
# trade
# ===========================================================
@app.route("/trade")
def trade():
    return """
    <h1>📈 Comprar Criptos</h1>
    BTC | XRP | WLD | ETH
    """
# ==========================================================
# 🔥 SWAP PRO DEFINITIVO CHC -> CHOROX
# Usa balance REAL del miner
# Quema CHC
# Envía CHOROX real BSC
# Cobra 1%
# Historial Mongo
# ==========================================================

from flask import request, session, redirect
from web3 import Web3
import os
import time

# ==========================================================
# CONFIG
# ==========================================================
BSC_RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(BSC_RPC))

ADMIN_ADDR = Web3.to_checksum_address(os.getenv("ADMIN_ADDR"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CHOROX = Web3.to_checksum_address("0x15681A8E9a8dF14946A4F852822B709e37b70c4E")

# 100 CHC = 1 CHOROX
RATE = 100

# ==========================================================
# ABI MINIMA ERC20
# ==========================================================
ERC20_ABI = [
{
"constant":False,
"inputs":[
{"name":"_to","type":"address"},
{"name":"_value","type":"uint256"}
],
"name":"transfer",
"outputs":[{"name":"","type":"bool"}],
"type":"function"
},
{
"constant":True,
"inputs":[{"name":"_owner","type":"address"}],
"name":"balanceOf",
"outputs":[{"name":"balance","type":"uint256"}],
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

token = w3.eth.contract(address=CHOROX, abi=ERC20_ABI)

# ==========================================================
# BALANCE REAL CHC
# ==========================================================
def chc_available(uid):

    row = wallets.find_one({"uid": uid})

    if not row:
        return 0

    addr = row["address"]

    pipeline = [
        {"$unwind":"$transacciones"},
        {"$match":{"transacciones.receptor":addr}},
        {"$group":{"_id":None,"total":{"$sum":"$transacciones.monto"}}}
    ]

    res = list(collection.aggregate(pipeline))

    mined = float(res[0]["total"]) if res else 0.0

    swapped = float(row.get("chc_swapped",0))

    return max(mined - swapped, 0)

# ==========================================================
# HOME BOTON
# ==========================================================
# agrega en home:
# <a class='btn swap' href='/swap'>🔄 Swap CHC ↔ CHOROX</a>

# ==========================================================
# PANEL SWAP
# ==========================================================
@app.route("/swap")
def swap():

    return """
    <html>
    <body style='background:#070b14;color:white;font-family:Arial;padding:20px'>

    <div style='max-width:600px;margin:auto;background:#111827;padding:25px;border-radius:20px'>

    <h2>🔄 Swap CHC → CHOROX</h2>

    <form method='post' action='/swap_now'>

    <input name='miner'
    placeholder='Dirección Minero CHC'
    style='width:100%;padding:14px;margin:8px 0'>

    <input name='seed'
    placeholder='Palabras / clave minera'
    style='width:100%;padding:14px;margin:8px 0'>

    <input name='amount'
    placeholder='Cantidad CHC'
    style='width:100%;padding:14px;margin:8px 0'>

    <input name='to'
    placeholder='Wallet BSC destino'
    style='width:100%;padding:14px;margin:8px 0'>

    <button style='width:100%;padding:16px;background:#10b981;color:white;border:0;border-radius:14px'>
    CAMBIAR AHORA
    </button>

    </form>

    </div>
    </body>
    </html>
    """

# ==========================================================
# EJECUTAR SWAP
# ==========================================================
@app.route("/swap_now", methods=["POST"])
def swap_now():

    def clean_seed(txt):
        txt = txt.strip().lower()
        txt = unicodedata.normalize("NFC", txt)
        txt = " ".join(txt.split())
        return txt

    miner = request.form["miner"].strip().lower()
    seed = clean_seed(request.form["seed"])
    amount = float(request.form["amount"])
    to = request.form["to"].strip()

    # verificar wallet minera existe
    row = wallets.find_one({
        "publica": miner,
        "semilla": seed
    })
    print("miner recibido:", miner)
    print("seed recibida:", seed)
    print("wallet encontrada:", row) 
    row = wallets.find_one({"publica": miner})
    print(row)
    if not row:
        return "❌ Wallet minera no válida"

    # calcular saldo real
    bal = balance_calc(miner)

    used = row.get("chc_swapped", 0)
    available = bal - used

    if amount > available:
        return "❌ Saldo insuficiente"

    # marcar usados
    wallets.update_one(
        {"_id": row["_id"]},
        {"$inc": {"chc_swapped": amount}}
    )

    # enviar CHOROX real
    send_chorox(to, amount)

    return "✅ Swap realizado"

    # ======================================================
    # CALCULO
    # ======================================================
    gross = amount / RATE
    fee = gross * 0.01
    send_tokens = gross - fee

    decimals = token.functions.decimals().call()

    qty = int(send_tokens * (10 ** decimals))

    # ======================================================
    # ENVIO CHOROX
    # ======================================================
    nonce = w3.eth.get_transaction_count(ADMIN_ADDR)

    tx = token.functions.transfer(
        to,
        qty
    ).build_transaction({
        "from": ADMIN_ADDR,
        "nonce": nonce,
        "gas": 120000,
        "gasPrice": w3.to_wei("3","gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)

    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    # ======================================================
    # QUEMAR / BLOQUEAR CHC
    # ======================================================
    wallets.update_one(
        {"uid": uid},
        {
            "$inc":{
                "chc_swapped": amount
            }
        }
    )

    # ======================================================
    # HISTORIAL
    # ======================================================
    swaps.insert_one({
        "uid": uid,
        "from": row["address"],
        "to": to,
        "chc": amount,
        "chorox": send_tokens,
        "fee": fee,
        "tx": tx_hash.hex(),
        "time": time.time()
    })

    return f"""
    <html>
    <body style='background:#070b14;color:white;font-family:Arial;padding:40px;text-align:center'>
    <h2>✅ Swap realizado</h2>
    <p>{amount} CHC cambiados</p>
    <p>Recibiste {round(send_tokens,6)} CHOROX</p>
    <p>TX:</p>
    <small>{tx_hash.hex()}</small><br><br>
    <a href='/swap' style='color:#00ff99'>Volver</a>
    </body>
    </html>
    """

# ==========================================================
# HISTORIAL
# ==========================================================
@app.route("/swap_history")
def swap_history():

    if "uid" not in session:
        return redirect("/wallet")

    uid = session["uid"]

    rows = swaps.find({"uid":uid}).sort("time",-1).limit(30)

    html = "<html><body style='background:#070b14;color:white;font-family:Arial;padding:20px'>"
    html += "<h2>Historial Swap</h2>"

    for x in rows:
        html += f"""
        <div style='background:#111827;padding:14px;border-radius:14px;margin-bottom:12px'>
        {x["chc"]} CHC → {round(x["chorox"],6)} CHOROX<br>
        <small>{x["tx"]}</small>
        </div>
        """

    html += "</body></html>"

    return html

# ============================================================
# prices
# ============================================================
@app.route("/prices")
def prices():
    import requests
    btc = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT").json()
    return btc

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
