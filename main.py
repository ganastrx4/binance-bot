import os
from pymongo import MongoClient
import hashlib
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURACIÓN DE MONGO (YA CONFIGURADO)
# ==========================================
MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
blockchain = db['blockchain']

DIFICULTAD = 5
RECOMPENSA = 18 
# ==========================================

def crear_genesis():
    try:
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
            print("[✨] Bloque Génesis creado en MongoDB Atlas.")
    except Exception as e:
        print(f"[❌] Error al conectar con MongoDB: {e}")

# RUTA PARA SERVIR EL EXPLORADOR (index.html)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# RUTA PARA RECIBIR MINEROS
@app.route('/minar', methods=['POST'])
def recibir_bloque():
    datos = request.json
    direccion = datos.get("wallet")
    nonce = datos.get("nonce")
    
    contenido = f"{direccion}{nonce}".encode()
    h = hashlib.sha256(contenido).hexdigest()
    
    if h.startswith("0" * DIFICULTAD):
        try:
            ultimo_bloque = list(blockchain.find().sort("indice", -1).limit(1))[0]
            nuevo_bloque = {
                "indice": ultimo_bloque["indice"] + 1,
                "timestamp": time.time(),
                "transacciones": [{"emisor": "SISTEMA", "receptor": direccion, "monto": RECOMPENSA, "tipo": "MINADO"}],
                "hash_anterior": ultimo_bloque["hash"],
                "nonce": nonce,
                "hash": h
            }
            blockchain.insert_one(nuevo_bloque)
            return jsonify({"status": "ok", "monto": RECOMPENSA}), 200
        except Exception as e:
            return jsonify({"status": "error", "mensaje": str(e)}), 500
            
    return jsonify({"status": "error", "mensaje": "Dificultad no alcanzada"}), 400

# RUTA PARA VER LA CADENA
@app.route('/cadena', methods=['GET'])
def ver_cadena():
    try:
        datos = list(blockchain.find({}, {"_id": 0}))
        return jsonify(datos), 200
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    crear_genesis()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
