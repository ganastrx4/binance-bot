# ============================================================
# app.py FIXED GODCHAIN V5 INSTITUTIONAL (CLEAN)
# ============================================================

import os
import time
import json
import hashlib
import secrets
import io
import requests
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template_string, session, send_file, redirect
from flask_cors import CORS

from pymongo import MongoClient, ASCENDING, DESCENDING
from web3 import Web3
from eth_account import Account

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")
CORS(app)

PORT = int(os.getenv("PORT", 10000))

# ============================================================
# MONGO
# ============================================================
MONGO_URI = os.getenv("MONGO_URI", "")
client = MongoClient(MONGO_URI)

db = client["charlycoin"]
collection = db["blockchain"]
wallets = db["wallets"]
claims = db["bonus_claims"]
swaps = db["swaps"]

# ============================================================
# WEB3 BSC
# ============================================================
RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(RPC))

ADMIN_ADDR = Web3.to_checksum_address(os.getenv("ADMIN_ADDR", "0x0000000000000000000000000000000000000000"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CHOROX = Web3.to_checksum_address("0x15681A8E9a8dF14946A4F852822B709e37b70c4E")

ERC20_ABI = [{
    "constant": False,
    "inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_value", "type": "uint256"}
    ],
    "name": "transfer",
    "outputs": [{"name": "", "type": "bool"}],
    "type": "function"
}, {
    "constant": True,
    "inputs": [{"name": "owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "", "type": "uint256"}],
    "type": "function"
}, {
    "constant": True,
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "type": "function"
}]

token = w3.eth.contract(address=CHOROX, abi=ERC20_ABI)

# ============================================================
# BLOCKCHAIN HELPERS
# ============================================================
def calc_hash(block):
    b = dict(block)
    b.pop("_id", None)
    b.pop("hash", None)
    return hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()

def reward():
    return 18.0

def balance_calc(wallet):
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]
    res = list(collection.aggregate(pipeline))
    return float(res[0]["total"]) if res else 0

# ============================================================
# WALLET
# ============================================================
def create_wallet():
    acct = Account.create()
    return {
        "address": acct.address,
        "private": acct.key.hex()
    }

def get_bnb(addr):
    try:
        return round(w3.from_wei(w3.eth.get_balance(addr), "ether"), 6)
    except:
        return 0

def get_chorox(addr):
    try:
        return token.functions.balanceOf(addr).call() / 10**18
    except:
        return 0

# ============================================================
# SEND TOKEN
# ============================================================
def send_chorox(to, amount):
    to = Web3.to_checksum_address(to)
    decimals = token.functions.decimals().call()
    value = int(amount * (10 ** decimals))

    nonce = w3.eth.get_transaction_count(ADMIN_ADDR)

    tx = token.functions.transfer(to, value).build_transaction({
        "chainId": 56,
        "gas": 120000,
        "gasPrice": w3.to_wei("3", "gwei"),
        "nonce": nonce,
        "from": ADMIN_ADDR
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()

# ============================================================
# GENESIS
# ============================================================
def crear_genesis():
    if collection.count_documents({}) == 0:
        b = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": "0",
            "hash_anterior": "0"
        }
        b["hash"] = calc_hash(b)
        collection.insert_one(b)

# ============================================================
# HOME + SCAN REEMPLAZO LIMPIO (PEGAR TAL CUAL)
# ============================================================

@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GODCHAIN HOME</title>

<style>
body{
margin:0;
font-family:Arial;
background:#050816;
color:white;
}

.top{
padding:40px;
background:linear-gradient(135deg,#2563eb,#0ea5e9,#111827);
text-align:center;
border-bottom-left-radius:30px;
border-bottom-right-radius:30px;
}

h1{
font-size:38px;
margin:0;
}

p{color:#cbd5e1}

.container{
max-width:1100px;
margin:auto;
padding:20px;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:15px;
margin-top:20px;
}

.card{
background:#0f172a;
padding:20px;
border-radius:18px;
border:1px solid #1e293b;
text-align:center;
}

a{
display:block;
padding:14px;
margin-top:10px;
border-radius:12px;
text-decoration:none;
color:white;
font-weight:700;
}

.wallet{background:#2563eb}
.scan{background:#06b6d4}
.swap{background:#10b981}
.stats{background:#f59e0b}

.footer{
text-align:center;
margin-top:30px;
color:#64748b;
font-size:12px;
}
</style>
</head>

<body>

<div class="top">
<h1>⚡ GODCHAIN V5</h1>
<p>CHC • CHOROX • WEB3 SYSTEM</p>
</div>

<div class="container">

<div class="grid">

<div class="card">
<h3>Wallet</h3>
<a class="wallet" href="/wallet">Abrir Wallet</a>
</div>

<div class="card">
<h3>Explorer</h3>
<a class="scan" href="/scan">CharlyScan</a>
</div>

<div class="card">
<h3>Swap</h3>
<a class="swap" href="/swap">CHC → CHOROX</a>
</div>

<div class="card">
<h3>Stats</h3>
<a class="stats" href="/stats">Ver Stats</a>
</div>

</div>

<div class="footer">
GODCHAIN NETWORK • LIVE
</div>

</div>

</body>
</html>
""")


@app.route("/scan")
def scan():
    return render_template_string("""<!DOCTYPE html>
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
</html>""")
# ============================================================
# WALLET
# ============================================================
@app.route("/wallet")
def wallet():
    if "uid" not in session:
        session["uid"] = secrets.token_hex(8)
        w = create_wallet()
        wallets.insert_one({"uid": session["uid"], **w})

    row = wallets.find_one({"uid": session["uid"]})
    addr = row["address"]

    return f"""
    <h2>Wallet</h2>
    <p>{addr}</p>
    <p>BNB: {get_bnb(addr)}</p>
    <p>CHOROX: {get_chorox(addr)}</p>
    """

# ============================================================
# BONUS CLAIM FIXED
# ============================================================
@app.route("/claim_bonus", methods=["POST"])
def claim_bonus():
    wallet = request.form.get("wallet", "").lower().strip()
    now = datetime.utcnow()

    row = claims.find_one({"wallet": wallet})

    if row:
        last = row["last_claim"]
        if now < last + timedelta(hours=24):
            return "⏳ Espera 24h"

    send_chorox(wallet, 100)

    claims.update_one(
        {"wallet": wallet},
        {"$set": {"last_claim": now}},
        upsert=True
    )

    return "✅ 100 CHOROX enviados"

# ============================================================
# STATS
# ============================================================
@app.route("/stats")
def stats():
    total = collection.count_documents({})
    return jsonify({
        "bloques": total,
        "recompensa": reward()
    })

# ============================================================
# CHAIN
# ============================================================
@app.route("/cadena")
def cadena():
    data = list(collection.find({}, {"_id": 0}).sort("indice", -1).limit(50))
    return jsonify(data)

# ============================================================
# BALANCE
# ============================================================
@app.route("/balance/<wallet>")
def balance(wallet):
    return jsonify({"balance": balance_calc(wallet)})

# ============================================================
# SWAP FIXED
# ============================================================
@app.route("/swap")
def swap():
    return """
    <h2>SWAP CHC → CHOROX</h2>
    <form method='post' action='/swap_now'>
    <input name='miner' placeholder='wallet'><br>
    <input name='amount' placeholder='amount'><br>
    <input name='to' placeholder='to'><br>
    <button>swap</button>
    </form>
    """

@app.route("/swap_now", methods=["POST"])
def swap_now():

    miner = request.form.get("miner","").lower().strip()
    amount = float(request.form.get("amount",0))
    to = request.form.get("to","")

    if balance_calc(miner) < amount:
        return "❌ no balance"

    send_chorox(to, amount)

    swaps.insert_one({
        "miner": miner,
        "to": to,
        "amount": amount,
        "time": time.time()
    })

    return "✅ swap ok"

# ============================================================
# BACKUP
# ============================================================
@app.route("/backup")
def backup():
    if "uid" not in session:
        return "no wallet"

    row = wallets.find_one({"uid": session["uid"]})

    mem = io.BytesIO()
    mem.write(json.dumps(row).encode())
    mem.seek(0)

    return send_file(mem, download_name="wallet.json", as_attachment=True)

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    crear_genesis()
    app.run(host="0.0.0.0", port=PORT)
