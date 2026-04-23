import hashlib
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN Y MONGODB
# ==========================================
# Usamos tu clave exacta: charly:caseta82%2A
MONGO_URI = "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
collection = db['blockchain']

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18
HALVING_CADA = 21000

# ==========================================
# 🧠 FUNCIONES BASE (MODIFICADAS PARA MONGO)
# ==========================================
def calcular_hash(bloque):
    # Quitamos el ID de Mongo para que el hash sea siempre el mismo
    bloque_copy = {k: v for k, v in bloque.items() if k != '_id' and k != 'hash'}
    bloque_string = json.dumps(bloque_copy, sort_keys=True).encode()
    return hashlib.sha256(bloque_string).hexdigest()

def crear_bloque_genesis():
    # Solo crea el génesis si la base de datos está vacía
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

def calcular_recompensa():
    bloques = collection.count_documents({})
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

    ultimo_bloque = collection.find_one(sort=[("indice", -1)])
    recompensa = calcular_recompensa()

    nuevo_bloque = {
        "indice": ultimo_bloque["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [
            {
                "emisor": "RED",
                "receptor": wallet,
                "monto": recompensa
            }
        ],
        "nonce": nonce,
        "hash_anterior": ultimo_bloque["hash"]
    }

    nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
    collection.insert_one(nuevo_bloque)

    return jsonify({
        "mensaje": "Bloque minado y guardado en Mongo",
        "recompensa": recompensa,
        "bloque": nuevo_bloque
    })

# ==========================================
# 📊 VER CADENA (LEYENDO DE MONGO)
# ==========================================
@app.route("/cadena", methods=["GET"])
def ver_cadena():
    # Trae todo de Mongo y quita el campo _id para que no de error el JSON
    blockchain = list(collection.find({}, {"_id": 0}))
    return jsonify(blockchain)

# ==========================================
# 💰 BALANCE
# ==========================================
@app.route("/balance/<wallet>", methods=["GET"])
def balance(wallet):
    total = 0
    blockchain = list(collection.find({}, {"_id": 0}))
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
