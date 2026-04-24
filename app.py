# ==========================================
# 🚀 CHARLYCOIN NODE FULL PRO DEFINITIVO
# Render + MongoDB + Anti Crash + Fast Chain
# Archivo: app.py
# ==========================================

import os
import json
import time
import hashlib
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient


# ==========================================
# APP
# ==========================================
app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIG
# ==========================================
PORT = int(os.environ.get("PORT", 10000))

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("Falta variable MONGO_URI en Render")

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000

# Anti spam minado
ULTIMO_MINADO = {}

# ==========================================
# MONGO PRO
# ==========================================
client = MongoClient(MONGO_URI)
db = client["charlycoin_db"]
collection = db["blockchain"]

collection.create_index("indice")

# ==========================================
# HTML SIMPLE
# ==========================================
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>CharlyCoin Node</title>
<style>
body{background:#07111c;color:#fff;font-family:Arial;padding:40px}
.box{background:#111827;padding:20px;border-radius:14px}
.green{color:#00ff88}
</style>
</head>
<body>
<div class="box">
<h1>🚀 CHARLYCOIN NODE</h1>
<p class="green">ONLINE</p>
<p>/cadena</p>
<p>/minar</p>
<p>/stats</p>
</div>
</body>
</html>
"""

# ==========================================
# HASH
# ==========================================
def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)

    texto = json.dumps(copia, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()

# ==========================================
# GENESIS
# ==========================================
def crear_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": 0,
            "hash_anterior": "0"
        }

        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

# ==========================================
# RECOMPENSA
# ==========================================
def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    recompensa = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(recompensa, 0.00000001)

# ==========================================
# HOME
# ==========================================
@app.route("/")
def home():
    return render_template_string(HTML)

# ==========================================
# STATUS
# ==========================================
@app.route("/health")
def health():
    return jsonify({"status": "online"})

# ==========================================
# STATS
# ==========================================
@app.route("/stats")
def stats():
    total = collection.count_documents({})
    return jsonify({
        "bloques": total - 1,
        "recompensa": recompensa_actual(),
        "dificultad": DIFICULTAD
    })

# ==========================================
# CADENA FAST
# ==========================================
@app.route("/cadena")
def cadena():

    datos = list(
        collection.find({}, {"_id": 0})
        .sort("indice", DESCENDING)
        .limit(100)
    )

    datos.reverse()

    return jsonify(datos)

# ==========================================
# BALANCE
# ==========================================
@app.route("/balance/<wallet>")
def balance(wallet):

    total = 0

    bloques = collection.find(
        {"transacciones.receptor": wallet},
        {"_id": 0}
    )

    for bloque in bloques:
        for tx in bloque["transacciones"]:
            if tx["receptor"] == wallet:
                total += tx["monto"]

    return jsonify({
        "wallet": wallet,
        "balance": total
    })

# ==========================================
# MINAR
# ==========================================
@app.route("/minar", methods=["POST"])
def minar():

    data = request.get_json(force=True)

    wallet = str(data.get("wallet", "")).strip()
    nonce = str(data.get("nonce", "")).strip()

    if not wallet:
        return jsonify({"error": "wallet requerida"}), 400

    # Anti spam (1 bloque cada 2 seg)
    ahora = time.time()

    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < 2:
            return jsonify({"error": "espera 2 segundos"}), 429

    # Validar POW
    prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "hash invalido"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])

    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [
            {
                "emisor": "RED",
                "receptor": wallet,
                "monto": recompensa_actual()
            }
        ],
        "nonce": nonce,
        "hash_anterior": ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)

    try:
        collection.insert_one(nuevo)

    except:
        return jsonify({"error": "bloque duplicado"}), 400

    ULTIMO_MINADO[wallet] = ahora

    return jsonify({
        "ok": True,
        "bloque": nuevo["indice"],
        "recompensa": nuevo["transacciones"][0]["monto"],
        "hash": nuevo["hash"]
    })

# ==========================================
# START
# ==========================================
if __name__ == "__main__":
    crear_genesis()
    app.run(host="0.0.0.0", port=PORT)
