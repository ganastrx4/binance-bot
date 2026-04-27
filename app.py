# ============================================================
# GODCHAIN EXCHANGE V5 INSTITUTIONAL (FIXED + PRO + FULL)
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
app.secret_key = os.getenv("SECRET_KEY", "godchain_v5")
CORS(app)

# ============================================================
# ENV
# ============================================================
ADMIN_ADDR = Web3.to_checksum_address(os.getenv("ADMIN_ADDR"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

MONGO_URI = os.getenv("MONGO_URI")
BSC_RPC = os.getenv("BSC_RPC", "https://bsc-dataseed.binance.org/")

CHC_RATE = float(os.getenv("CHC_RATE", "100"))

# ============================================================
# DB
# ============================================================
client = MongoClient(MONGO_URI)
db = client[os.getenv("DB_NAME", "godchain")]

wallets = db["wallets"]
chain = db["chain"]
swaps = db["swaps"]
claims = db["claims"]

# ============================================================
# WEB3
# ============================================================
w3 = Web3(Web3.HTTPProvider(BSC_RPC))

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
    return float(r[0]["t"]) if r else 0.0

def chorox_balance(addr):
    try:
        return token.functions.balanceOf(addr).call() / 10**18
    except:
        return 0

# ============================================================
# FRONT
# ============================================================
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>GODCHAIN V5</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#05070f;color:white;font-family:Arial}
.box{max-width:520px;margin:auto;padding:20px}
.card{background:#111827;padding:20px;border-radius:20px}
input,button{width:100%;padding:14px;margin-top:10px;border-radius:12px;border:none}
button{background:#10b981;color:white;font-weight:bold}
h1{color:#22c55e}
.small{color:#94a3b8}
</style>
</head>
<body>
<div class="box">

<h1>⚡ GODCHAIN V5</h1>

<div class="card">

<button onclick="wallet()">🔐 WALLET</button>

<p id="addr" class="small"></p>
<p id="bal"></p>

<hr>

<h3>🔄 SWAP CHC → CHOROX</h3>

<input id="amount" placeholder="CHC">
<input id="to" placeholder="BSC wallet">

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
 document.getElementById("addr").innerText = addr
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
# WALLET
# ============================================================
@app.route("/wallet")
def wallet():

    if "uid" not in session:
        uid = secrets.token_hex(8)
        w = create_wallet()
        wallets.insert_one({"uid": uid, **w, "used": 0})
        session["uid"] = uid

    w = wallets.find_one({"uid": session["uid"]})

    return jsonify({
        "address": w["address"],
        "chorox": chorox_balance(w["address"])
    })

# ============================================================
# MINERIA
# ============================================================
@app.route("/minar", methods=["POST"])
def minar():

    data = request.json
    wallet = data.get("wallet")
    nonce = data.get("nonce")

    h = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not h.startswith("0000"):
        return jsonify({"error":"invalid"}),400

    last = chain.find_one(sort=[("index",-1)]) or {"index":0}

    chain.insert_one({
        "index": last["index"]+1,
        "tx":[{"to":wallet,"amount":10}]
    })

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

        nonce = w3.eth.get_transaction_count(ADMIN_ADDR)

        tx = token.functions.transfer(
            wallet,
            int(100*10**18)
        ).build_transaction({
            "from":ADMIN_ADDR,
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
# SWAP FIXED (NO ERROR "NO BALANCE")
# ============================================================
@app.route("/swap", methods=["POST"])
def swap():

    uid = session.get("uid")
    data = request.json

    amount = float(data.get("amount",0))
    to = data.get("to")

    if not uid:
        return jsonify({"error":"no session"}),403

    user = wallets.find_one({"uid":uid})
    if not user:
        return jsonify({"error":"no wallet"}),404

    mined = chc_balance(user["address"])
    used = float(user.get("used",0))
    available = mined - used

    if available <= 0:
        return jsonify({"error":"no CHC mined"}),400

    if amount > available:
        return jsonify({"error":"insufficient CHC","available":available}),400

    wallets.update_one({"uid":uid},{"$inc":{"used":amount}})

    if PRIVATE_KEY:

        send = (amount / CHC_RATE) * 0.99

        nonce = w3.eth.get_transaction_count(ADMIN_ADDR)

        tx = token.functions.transfer(
            to,
            int(send * 10**18)
        ).build_transaction({
            "from":ADMIN_ADDR,
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

    return jsonify({
        "ok":True,
        "spent_chc":amount,
        "sent_chorox":send
    })

# ============================================================
# BALANCE CHC
# ============================================================
@app.route("/balance/<w>")
def balance(w):
    return jsonify({"chc":chc_balance(w)})

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
