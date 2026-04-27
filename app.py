# ============================================================
# app.py V10 LIMPIO TOTAL
# CHC + Wallet + Explorer + Bonus + Prices
# Render Ready
# ============================================================

import os
import io
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import (
    Flask, request, jsonify,
    session, send_file
)
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING, ASCENDING
import requests

# ============================================================
# APP
# ============================================================

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "charly_v10_key")
CORS(app)

PORT = int(os.getenv("PORT", 10000))

# ============================================================
# MONGO
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "").strip()

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client["charlycoin_db"]

collection = db["blockchain"]
wallets = db["wallets"]
claims = db["bonus_claims"]

collection.create_index("hash")
wallets.create_index("uid", unique=True)

try:
    collection.create_index([("indice", ASCENDING)], unique=True)
except:
    pass

# ============================================================
# CONFIG CHC
# ============================================================

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000

ULTIMO_MINADO = {}

# ============================================================
# HELPERS
# ============================================================

def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)

    texto = json.dumps(
        copia,
        sort_keys=True
    ).encode()

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

    bloques = max(collection.count_documents({}) - 1, 0)

    halvings = bloques // HALVING_CADA

    reward = RECOMPENSA_INICIAL / (2 ** halvings)

    if reward < 0.00000001:
        reward = 0.00000001

    return reward


def create_wallet():
    return {
        "address": "CHC_" + secrets.token_hex(20),
        "private_key": secrets.token_hex(32),
        "seed": secrets.token_hex(16)
    }


def balance_calc(wallet):

    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": wallet}},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$transacciones.monto"}
        }}
    ]

    res = list(collection.aggregate(pipeline))

    return round(res[0]["total"], 4) if res else 0


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return """
    <html>
    <body style='background:#0b1220;color:white;
    font-family:Arial;padding:30px'>

    <h1>💎 CHC SUPER APP V10</h1>

    <p>Wallet + Minería + Explorer + Bonus</p>

    <hr>

    <a href='/wallet'>💼 Wallet</a><br><br>
    <a href='/scan'>⛓ Explorer</a><br><br>
    <a href='/stats'>📊 Stats</a><br><br>
    <a href='/prices'>📈 Binance Prices</a><br><br>

    <hr>

    <form method='post' action='/claim_bonus'>
    <input name='wallet' placeholder='Wallet'>
    <button>🎁 Reclamar Bonus</button>
    </form>

    </body>
    </html>
    """


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

    bal = balance_calc(addr)

    return f"""
    <html>
    <body style='background:#111;color:white;
    font-family:Arial;padding:30px'>

    <h1>💼 CHC Wallet</h1>

    <p><b>Address:</b><br>{addr}</p>

    <p><b>Balance:</b> {bal} CHC</p>

    <p><b>Seed:</b> {row["seed"]}</p>

    <a href='/backup'>📥 Backup</a><br><br>
    <a href='/'>🏠 Inicio</a>

    </body>
    </html>
    """


# ============================================================
# BACKUP
# ============================================================

@app.route("/backup")
def backup():

    if "uid" not in session:
        return "No wallet"

    row = wallets.find_one({"uid": session["uid"]})

    data = {
        "address": row["address"],
        "private_key": row["private_key"],
        "seed": row["seed"]
    }

    mem = io.BytesIO()
    mem.write(json.dumps(data, indent=4).encode())
    mem.seek(0)

    return send_file(
        mem,
        as_attachment=True,
        download_name="wallet_backup.json",
        mimetype="application/json"
    )


# ============================================================
# BONUS
# ============================================================

@app.route("/claim_bonus", methods=["POST"])
def claim_bonus():

    wallet = request.form["wallet"].strip()
    now = datetime.utcnow()

    row = claims.find_one({"wallet": wallet})

    if row:

        next_time = row["last_claim"] + timedelta(hours=24)

        if now < next_time:

            faltan = next_time - now

            horas = int(faltan.total_seconds() // 3600)
            mins = int((faltan.total_seconds() % 3600) // 60)

            return f"⏳ Espera {horas}h {mins}m"

    if balance_calc(wallet) <= 0:
        return "❌ Debes minar CHC primero"

    claims.update_one(
        {"wallet": wallet},
        {"$set": {"last_claim": now}},
        upsert=True
    )

    return "✅ Bonus reclamado"


# ============================================================
# STATS
# ============================================================

@app.route("/stats")
def stats():

    total = max(collection.count_documents({}) - 1, 0)

    pipeline = [
        {"$unwind": "$transacciones"},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$transacciones.monto"}
        }}
    ]

    result = list(collection.aggregate(pipeline))

    supply = result[0]["total"] if result else 0

    return jsonify({
        "bloques": total,
        "supply": round(float(supply), 4),
        "reward": recompensa_actual(),
        "dificultad": DIFICULTAD
    })


# ============================================================
# BALANCE API
# ============================================================

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

    wallet = str(data.get("wallet", "")).strip()
    nonce = str(data.get("nonce", "")).strip()

    if not wallet or not nonce:
        return jsonify({"error": "faltan datos"}), 400

    ahora = time.time()

    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < 2:
            return jsonify({"error": "espera"}), 429

    prueba = hashlib.sha256(
        f"{wallet}{nonce}".encode()
    ).hexdigest()

    if not prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "hash invalido"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])

    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": ahora,
        "transacciones": [{
            "emisor": "RED",
            "receptor": wallet,
            "monto": recompensa_actual()
        }],
        "nonce": nonce,
        "hash_anterior": ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)

    collection.insert_one(nuevo)

    ULTIMO_MINADO[wallet] = ahora

    return jsonify({
        "ok": True,
        "bloque": nuevo["indice"]
    })


# ============================================================
# EXPLORER
# ============================================================

@app.route("/cadena")
def cadena():

    datos = list(
        collection.find({}, {"_id": 0})
        .sort("indice", DESCENDING)
        .limit(50)
    )

    return jsonify(datos)


@app.route("/scan")
def scan():
    return """
    <html>
    <body style='background:#000;color:#0f0;
    font-family:monospace;padding:20px'>

    <h1>⛓ CHC Explorer</h1>

    <p>Usa /cadena para ver bloques JSON</p>

    <a href='/cadena' style='color:cyan'>Abrir cadena</a>

    </body>
    </html>
    """


# ============================================================
# PRICES
# ============================================================

@app.route("/prices")
def prices():

    pares = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "WLDUSDT"]

    out = {}

    for p in pares:
        try:
            r = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": p},
                timeout=10
            ).json()

            out[p] = r["price"]

        except:
            out[p] = "error"

    return jsonify(out)


# ============================================================
# TEST
# ============================================================

@app.route("/test")
def test():
    return "ok"


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    crear_genesis()
    app.run(host="0.0.0.0", port=PORT)
