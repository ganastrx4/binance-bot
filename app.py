# ============================================================
# APP.PY V4 GODCHAIN EXCHANGE (CLEAN + FUNCIONAL)
# ============================================================

import os
import time
import json
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, session, send_file, redirect
from flask_cors import CORS
from pymongo import MongoClient
from web3 import Web3
from eth_account import Account

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "godchain_key")
CORS(app)

# ============================================================
# MONGO
# ============================================================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["godchain"]

wallets = db["wallets"]
chain = db["chain"]
swaps = db["swaps"]
claims = db["claims"]

# ============================================================
# BSC / WEB3
# ============================================================
RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(RPC))

ADMIN = Web3.to_checksum_address(os.getenv("ADMIN_ADDR", "0x0000000000000000000000000000000000000000"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

TOKEN = Web3.to_checksum_address("0x15681A8E9a8dF14946A4F852822b709e37b70c4E")

ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "outputs": [{"type": "bool"}],
        "constant": False
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"type": "uint256"}],
        "constant": True
    }
]

token = w3.eth.contract(address=TOKEN, abi=ERC20_ABI)

# ============================================================
# HELPERS
# ============================================================
def create_wallet():
    acct = Account.create()
    return {
        "address": acct.address,
        "private": acct.key.hex()
    }

def get_chorox(addr):
    try:
        bal = token.functions.balanceOf(addr).call()
        return bal / 10**18
    except:
        return 0

def hash_block(block):
    b = dict(block)
    b.pop("_id", None)
    return hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()

def chc_balance(wallet):
    data = chain.aggregate([
        {"$unwind": "$tx"},
        {"$match": {"tx.to": wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$tx.amount"}}}
    ])
    res = list(data)
    return res[0]["total"] if res else 0

# ============================================================
# WALLET SESSION
# ============================================================
@app.route("/wallet")
def wallet():
    if "uid" not in session:
        uid = secrets.token_hex(8)
        w = create_wallet()
        wallets.insert_one({"uid": uid, **w, "chc_swapped": 0})
        session["uid"] = uid

    w = wallets.find_one({"uid": session["uid"]})

    return jsonify({
        "address": w["address"],
        "chorox": get_chorox(w["address"])
    })

# ============================================================
# MINAR CHC
# ============================================================
@app.route("/minar", methods=["POST"])
def minar():
    data = request.json
    wallet = data.get("wallet")
    nonce = data.get("nonce")

    if not wallet or not nonce:
        return jsonify({"error": "missing"}), 400

    h = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not h.startswith("0000"):
        return jsonify({"error": "invalid"}), 400

    last = chain.find_one(sort=[("index", -1)]) or {"index": 0}

    block = {
        "index": last["index"] + 1,
        "time": time.time(),
        "tx": [{"to": wallet, "amount": 10}]
    }

    block["hash"] = hash_block(block)
    chain.insert_one(block)

    return jsonify({"ok": True})

# ============================================================
# CLAIM BONUS CHOROX
# ============================================================
@app.route("/claim", methods=["POST"])
def claim():
    wallet = request.json.get("wallet")
    now = datetime.utcnow()

    row = claims.find_one({"wallet": wallet})

    if row and now < row["next"]:
        return jsonify({"error": "cooldown"}), 429

    # SEND REAL TOKEN
    if PRIVATE_KEY:
        nonce = w3.eth.get_transaction_count(ADMIN)
        tx = token.functions.transfer(
            wallet,
            int(100 * 10**18)
        ).build_transaction({
            "from": ADMIN,
            "nonce": nonce,
            "gas": 120000,
            "gasPrice": w3.to_wei("3", "gwei")
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        w3.eth.send_raw_transaction(signed.raw_transaction)

    claims.update_one(
        {"wallet": wallet},
        {"$set": {"next": now + timedelta(hours=24)}},
        upsert=True
    )

    return jsonify({"ok": True})

# ============================================================
# SWAP CHC -> CHOROX
# ============================================================
@app.route("/swap", methods=["POST"])
def swap():

    uid = session.get("uid")
    data = request.json

    amount = float(data.get("amount", 0))
    to = data.get("to")

    if not uid:
        return jsonify({"error": "no session"}), 403

    user = wallets.find_one({"uid": uid})
    if not user:
        return jsonify({"error": "no wallet"}), 404

    mined = chc_balance(user["address"])
    used = user.get("chc_swapped", 0)

    if amount > (mined - used):
        return jsonify({"error": "insufficient"}), 400

    # mark used
    wallets.update_one(
        {"uid": uid},
        {"$inc": {"chc_swapped": amount}}
    )

    # send CHOROX
    if PRIVATE_KEY:
        gross = amount / 100
        fee = gross * 0.01
        send = gross - fee

        nonce = w3.eth.get_transaction_count(ADMIN)

        tx = token.functions.transfer(
            to,
            int(send * 10**18)
        ).build_transaction({
            "from": ADMIN,
            "nonce": nonce,
            "gas": 120000,
            "gasPrice": w3.to_wei("3", "gwei")
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    swaps.insert_one({
        "uid": uid,
        "amount_chc": amount,
        "to": to,
        "time": time.time()
    })

    return jsonify({"ok": True})

# ============================================================
# BALANCE
# ============================================================
@app.route("/balance/<wallet>")
def balance(wallet):
    return jsonify({"chc": chc_balance(wallet)})

# ============================================================
# CHAIN
# ============================================================
@app.route("/chain")
def get_chain():
    data = list(chain.find({}, {"_id": 0}).sort("index", -1).limit(50))
    return jsonify(data)

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
