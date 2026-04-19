import os
from pymongo import MongoClient
import hashlib
import time
from flask import Flask, request, jsonify
from flask_cors import CORS # Esto es para que tu GitHub pueda leer los datos

app = Flask(__name__)
CORS(app) # Permite que tu web de GitHub acceda a la info

# ==========================================
# CONFIGURACIÓN DE MONGO
# ==========================================
# PEGA AQUÍ TU LINK (REEMPLAZA <db_password> POR TU CONTRASEÑA REAL)
MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
blockchain = db['blockchain']

DIFICULTAD = 5
RECOMPENSA = 18 
# ==========================================

def crear_genesis():
    if blockchain.count_documents({}) == 0:
        genesis = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [{"emisor": "SISTEMA", "receptor": "GENESIS", "monto": 0}],
            "hash_anterior": "0",
            "nonce": 0,
            "hash": "0"
        }
        blockchain.insert_one(genesis)
        print("[✨] Bloque Génesis creado en MongoDB.")

@app.route('/minar', methods=['POST'])
def recibir_bloque():
    datos = request.json
    direccion = datos.get("wallet")
    nonce = datos.get("nonce")
    
    # Validar el esfuerzo (Proof of Work)
    contenido = f"{direccion}{nonce}".encode()
    h = hashlib.sha256(contenido).hexdigest()
    
    if h.startswith("0" * DIFICULTAD):
        ultimo_bloque = list(blockchain.find().sort("indice", -1).limit(1))[0]
        
        nuevo_bloque = {
            "indice": ultimo_bloque["indice"] + 1,
            "timestamp": time.time(),
            "transacciones": [{
                "emisor": "SISTEMA",
                "receptor": direccion,
                "monto": RECOMPENSA,
                "tipo": "MINADO"
            }],
            "hash_anterior": ultimo_bloque["hash"],
            "nonce": nonce,
            "hash": h
        }
        blockchain.insert_one(nuevo_bloque)
        return jsonify({"status": "ok", "monto": RECOMPENSA}), 200
    return jsonify({"status": "error", "mensaje": "Faltan ceros de dificultad"}), 400

@app.route('/cadena', methods=['GET'])
def ver_cadena():
    # Esto es lo que consultará tu página de GitHub
    datos = list(blockchain.find({}, {"_id": 0}))
    return jsonify(datos), 200

if __name__ == "__main__":
    crear_genesis()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
