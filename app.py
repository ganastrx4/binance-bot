# ============================================================
# GODCHAIN V4 EXCHANGE FULL (BACKEND + FRONTEND)
# ============================================================

import os
import time
import json
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, session, render_template_string
from flask_cors import CORS
from pymongo import MongoClient
from web3 import Web3
from eth_account import Account

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "godchain")
CORS(app)

# ============================================================
# DB
# ============================================================
client = MongoClient(os.getenv("MONGO_URI"))
db = client["godchain"]

wallets = db["wallets"]
chain = db["chain"]
swaps = db["swaps"]
claims = db["claims"]

# ============================================================
# WEB3 BSC
# ============================================================
w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

ADMIN = Web3.to_checksum_address(os.getenv("ADMIN_ADDR", "0x0000000000000000000000000000000000000000"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

TOKEN = Web3.to_checksum_address("0x15681A8E9a8dF14946A4F852822b709e37b70c4E")

ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "outputs": [{"type": "bool"}]
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "a", "type": "address"}],
        "outputs": [{"type": "uint256"}]
    }
]

token = w3.eth.contract(address=TOKEN, abi=ABI)

# ============================================================
# HELPERS
# ============================================================
def create_wallet():
    acct = Account.create()
    return {"address": acct.address, "private": acct.key.hex()}

def chc_balance(addr):
    res = chain.aggregate([
        {"$unwind": "$tx"},
        {"$match": {"tx.to": addr}},
        {"$group": {"_id": None, "t": {"$sum": "$tx.amount"}}}
    ])
    r = list(res)
    return r[0]["t"] if r else 0

# ============================================================
# HOME FRONTEND EXCHANGE
# ============================================================
@app.route("/")
def home():

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>GODCHAIN EXCHANGE</title>
<meta name="viewport" content="width=device-width,initial-scale=1">

<style>
body{margin:0;background:#070b14;color:white;font-family:Arial}
.box{max-width:500px;margin:auto;padding:20px}
.card{background:#111827;padding:20px;border-radius:20px}
input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#0b1220;color:white}
button{width:100%;padding:14px;border:none;border-radius:12px;background:#10b981;color:white;font-weight:bold}
h1{color:#22c55e}
.small{color:#94a3b8;font-size:13px}
hr{border:1px solid #1f2937}
</style>
</head>

<body>

<div class="box">

<h1>⚡ GODCHAIN EXCHANGE</h1>

<div class="card">

<button onclick="wallet()">🔐 Crear / Ver Wallet</button>

<p id="addr" class="small"></p>
<p id="bal"></p>

<hr>

<h3>🔄 Swap CHC → CHOROX</h3>

<input id="amount" placeholder="CHC">
<input id="to" placeholder="Wallet BSC destino">

<button onclick="swap()">SWAP</button>

<p id="msg"></p>

</div>
</div>

<script>

let addr="";

async function wallet(){
 let r = await fetch("/wallet")
 let d = await r.json()
 addr = d.address
 document.getElementById("addr").innerText = "Wallet: "+addr
 document.getElementById("bal").innerText = "CHOROX: "+d.chorox
}

async function swap(){

 let amount = document.getElementById("amount").value
 let to = document.getElementById("to").value

 let r = await fetch("/swap",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({amount,to})
 })

 let d = await r.json()
 document.getElementById("msg").innerText = JSON.stringify(d)
}

</script>

</body>
</html>
""")

# ============================================================
# WALLET SESSION
# ============================================================
@app.route("/wallet")
def wallet():

    if "uid" not in session:
        uid = secrets.token_hex(8)
        w = create_wallet()
        wallets.insert_one({"uid": uid, **w, "used": 0})
        session["uid"] = uid

    w = wallets.find_one({"uid": session["uid"]})

    bal = token.functions.balanceOf(w["address"]).call() / 10**18

    return jsonify({
        "address": w["address"],
        "chorox": bal
    })

# ============================================================
# MINERIA CHC
# ============================================================
@app.route("/minar", methods=["POST"])
def minar():

    data = request.json
    wallet = data["wallet"]
    nonce = data["nonce"]

    h = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not h.startswith("0000"):
        return jsonify({"error": "fail"}),400

    last = chain.find_one(sort=[("index",-1)]) or {"index":0}

    block = {
        "index": last["index"]+1,
        "tx":[{"to":wallet,"amount":10}]
    }

    chain.insert_one(block)

    return jsonify({"ok":True})

# ============================================================
# CLAIM
# ============================================================
@app.route("/claim", methods=["POST"])
def claim():

    wallet = request.json["wallet"]
    now = datetime.utcnow()

    c = claims.find_one({"wallet":wallet})

    if c and now < c["next"]:
        return jsonify({"error":"cooldown"}),429

    if PRIVATE_KEY:
        nonce = w3.eth.get_transaction_count(ADMIN)

        tx = token.functions.transfer(
            wallet,
            int(100*10**18)
        ).build_transaction({
            "from":ADMIN,
            "nonce":nonce,
            "gas":120000,
            "gasPrice":w3.to_wei("3","gwei")
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed.raw_transaction)

    claims.update_one(
        {"wallet":wallet},
        {"$set":{"next":now+timedelta(hours=24)}},
        upsert=True
    )

    return jsonify({"ok":True})

# ============================================================
# SWAP CHC -> CHOROX
# ============================================================
@app.route("/swap", methods=["POST"])
def swap():

    uid = session.get("uid")
    data = request.json

    amount = float(data["amount"])
    to = data["to"]

    user = wallets.find_one({"uid":uid})
    if not user:
        return jsonify({"error":"no wallet"}),404

    mined = chc_balance(user["address"])
    used = user.get("used",0)

    if amount > mined-used:
        return jsonify({"error":"no balance"}),400

    wallets.update_one({"uid":uid},{"$inc":{"used":amount}})

    if PRIVATE_KEY:

        send = (amount/100)*0.99

        nonce = w3.eth.get_transaction_count(ADMIN)

        tx = token.functions.transfer(
            to,
            int(send*10**18)
        ).build_transaction({
            "from":ADMIN,
            "nonce":nonce,
            "gas":120000,
            "gasPrice":w3.to_wei("3","gwei")
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed.raw_transaction)

    swaps.insert_one({
        "uid":uid,
        "amount":amount,
        "to":to,
        "time":time.time()
    })

    return jsonify({"ok":True})

# ============================================================
# BALANCE CHC
# ============================================================
@app.route("/balance/<w>")
def balance(w):
    return jsonify({"chc":chc_balance(w)})

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
