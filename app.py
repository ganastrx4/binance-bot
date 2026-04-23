import hashlib
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN
# ==========================================
DIFICULTAD = 5
RECOMPENSA_INICIAL = 18
HALVING_CADA = 21000

blockchain = []
pending_tx = []

# ==========================================
# 🧠 FUNCIONES BASE
# ==========================================
def calcular_hash(bloque):
    bloque_string = json.dumps(bloque, sort_keys=True).encode()
    return hashlib.sha256(bloque_string).hexdigest()

def crear_bloque_genesis():
    bloque = {
        "indice": 0,
        "timestamp": time.time(),
        "transacciones": [],
        "nonce": 0,
        "hash_anterior": "0"
    }
    bloque["hash"] = calcular_hash(bloque)
    blockchain.append(bloque)

def calcular_recompensa():
    bloques = len(blockchain)
    halvings = bloques // HALVING_CADA
    recompensa = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(recompensa, 0.00000001)

# ==========================================
# ⛏️ MINAR BLOQUE
# ==========================================
@app.route("/minar", methods=["POST"])
def minar():
    data = request.json
    wallet = data.get("wallet")
    nonce = data.get("nonce")

    if not wallet:
        return jsonify({"error": "Wallet requerida"}), 400

    hash_prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not hash_prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "Hash inválido"}), 400

    recompensa = calcular_recompensa()

    nuevo_bloque = {
        "indice": len(blockchain),
        "timestamp": time.time(),
        "transacciones": [
            {
                "emisor": "RED",
                "receptor": wallet,
                "monto": recompensa
            }
        ],
        "nonce": nonce,
        "hash_anterior": blockchain[-1]["hash"]
    }

    nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
    blockchain.append(nuevo_bloque)

    return jsonify({
        "mensaje": "Bloque minado",
        "recompensa": recompensa,
        "bloque": nuevo_bloque
    })

# ==========================================
# 📊 VER CADENA
# ==========================================
@app.route("/cadena", methods=["GET"])
def ver_cadena():
    return jsonify(blockchain)

# ==========================================
# 💰 BALANCE
# ==========================================
@app.route("/balance/<wallet>", methods=["GET"])
def balance(wallet):
    total = 0
    for bloque in blockchain:
        for tx in bloque["transacciones"]:
            if tx["receptor"] == wallet:
                total += tx["monto"]
            if tx["emisor"] == wallet:
                total -= tx["monto"]

    return jsonify({"wallet": wallet, "balance": total})

# ==========================================
# 🚀 INICIO
# ==========================================
if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
