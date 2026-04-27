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
# HOME
# ============================================================
@app.route("/")
def home():
    return "<h1>GODCHAIN ONLINE</h1>"

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
