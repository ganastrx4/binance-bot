import os
import time
import hashlib
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
PORT = int(os.environ.get("PORT", 10000))
MONGO_URI = os.environ.get("MONGO_URI", "")

if not MONGO_URI:
    MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority"

DIFICULTAD = 5
RECOMPENSA = 18.0
CHOROX_RATE = 1  # 1 CHC = 1 CHOROX (ajústalo)

client = MongoClient(MONGO_URI)
db = client["charlycoin_db"]

chain = db["blockchain"]
wallets = db["wallets"]
txs = db["transacciones"]

try:
    chain.create_index([("indice", ASCENDING)], unique=True)
except Exception as e:
    print("Index ya existe:", e)

# =========================
# GENESIS
# =========================
def genesis():
    if chain.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "hash_anterior": "0",
            "nonce": "0"
        }
        bloque["hash"] = hashlib.sha256(json.dumps(bloque).encode()).hexdigest()
        chain.insert_one(bloque)

# =========================
# HASH
# =========================
def hash_block(b):
    b = dict(b)
    b.pop("_id", None)
    b.pop("hash", None)
    return hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()

# =========================
# BALANCE
# =========================
@app.route("/balance/<wallet>")
def balance(wallet):
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]
    res = list(chain.aggregate(pipeline))
    return jsonify({"balance": res[0]["total"] if res else 0})

# =========================
# MINAR
# =========================
@app.route("/minar", methods=["POST"])
def minar():
    data = request.get_json()
    wallet = data.get("wallet")
    nonce = data.get("nonce")

    if not wallet:
        return jsonify({"error": "wallet faltante"}), 400

    h = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not h.startswith("0" * DIFICULTAD):
        return jsonify({"error": "invalid hash"}), 400

    last = chain.find_one(sort=[("indice", -1)])

    bloque = {
        "indice": last["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{
            "emisor": "RED",
            "receptor": wallet,
            "monto": RECOMPENSA
        }],
        "nonce": nonce,
        "hash_anterior": last["hash"]
    }

    bloque["hash"] = hash_block(bloque)
    chain.insert_one(bloque)

    # crear wallet si no existe
    if not wallets.find_one({"wallet": wallet}):
        wallets.insert_one({"wallet": wallet, "chc": 0, "chorox": 0})

    wallets.update_one(
        {"wallet": wallet},
        {"$inc": {"chc": RECOMPENSA}},
        upsert=True
    )

    return jsonify({"ok": True})

# =========================
# TRANSFERIR CHC
# =========================
@app.route("/transferir", methods=["POST"])
def transferir():
    d = request.get_json()

    emisor = d["emisor"]
    receptor = d["receptor"]
    monto = float(d["monto"])

    w1 = wallets.find_one({"wallet": emisor})
    if not w1:
        return jsonify({"error": "wallet emisor no existe"}), 404

    if w1["chc"] < monto:
        return jsonify({"error": "saldo insuficiente"}), 400

    wallets.update_one({"wallet": emisor}, {"$inc": {"chc": -monto}}, upsert=True)
    wallets.update_one({"wallet": receptor}, {"$inc": {"chc": monto}}, upsert=True)

    return jsonify({"ok": True})

# =========================
# SWAP CHC → CHOROX (MINT + BURN)
# =========================
@app.route("/swap", methods=["POST"])
def swap():
    data = request.get_json()
    wallet = data.get("wallet")
    amount = float(data.get("amount"))

    w = wallets.find_one({"wallet": wallet})
    if not w or w["chc"] < amount:
        return jsonify({"error": "sin fondos"}), 400

    # burn CHC
    wallets.update_one({"wallet": wallet}, {"$inc": {"chc": -amount}})

    # mint CHOROX
    chorox = amount * CHOROX_RATE
    wallets.update_one({"wallet": wallet}, {"$inc": {"chorox": chorox}})

    return jsonify({
        "ok": True,
        "burned_chc": amount,
        "minted_chorox": chorox
    })

# =========================
# STATS
# =========================
@app.route("/stats")
def stats():
    return jsonify({
        "bloques": chain.count_documents({}),
        "supply": chain.count_documents({}) * RECOMPENSA
    })

# =========================
# BLOCKCHAIN
# =========================
@app.route("/cadena")
def cadena():
    return jsonify(list(chain.find({}, {"_id": 0}).sort("indice", DESCENDING).limit(50)))

# =========================
# INIT
# =========================
if __name__ == "__main__":
    genesis()
    app.run(host="0.0.0.0", port=PORT)
