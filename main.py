import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
import hashlib
import time
import binascii
import ecdsa

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURACIÓN DE MONGO
# ==========================================
MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
blockchain = db['blockchain']

DIFICULTAD = 5
RECOMPENSA_MINADO = 18.0

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def obtener_saldo(address):
    """Calcula el saldo sumando recompensas y restando envíos"""
    balance = 0.0
    # Sumar lo que ha recibido (por minado o transferencias)
    for bloque in blockchain.find({"transacciones.receptor": address}):
        for tx in bloque["transacciones"]:
            if tx["receptor"] == address:
                balance += float(tx["monto"])
    
    # Restar lo que ha enviado
    for bloque in blockchain.find({"transacciones.emisor": address}):
        for tx in bloque["transacciones"]:
            if tx["emisor"] == address:
                balance -= float(tx["monto"])
    return balance

def verificar_firma(public_key_hex, mensaje, firma_hex):
    """Valida que la firma digital sea auténtica"""
    try:
        public_key_bytes = binascii.unhexlify(public_key_hex)
        vk = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)
        return vk.verify(binascii.unhexlify(firma_hex), mensaje.encode())
    except:
        return False

# ==========================================
# RUTAS DEL SERVIDOR
# ==========================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Agrega esta ruta a tu main.py actual en Render/GitHub

@app.route('/transferir', methods=['POST'])
def transferir():
    datos = request.json
    emisor = datos.get("emisor")
    receptor = datos.get("receptor")
    monto = float(datos.get("monto"))
    firma = datos.get("firma")

    # 1. Creamos el mensaje para validar la firma
    # Debe ser exactamente igual a como se armó en el minero
    mensaje = f"{emisor}{receptor}{monto}".encode()

    try:
        # 2. Validamos la firma digital
        public_key_bytes = binascii.unhexlify(emisor)
        vk = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)
        
        # Si la firma no coincide, soltará un error y pasará al 'except'
        vk.verify(binascii.unhexlify(firma), mensaje)
        
        # 3. (Opcional pero recomendado) Verificar saldo en MongoDB
        # Aquí puedes agregar lógica para ver si el emisor tiene saldo suficiente
        
        # 4. Registrar en MongoDB
        ultimo_bloque = list(blockchain.find().sort("indice", -1).limit(1))[0]
        nuevo_bloque = {
            "indice": ultimo_bloque["indice"] + 1,
            "timestamp": time.time(),
            "transacciones": [{
                "emisor": emisor,
                "receptor": receptor,
                "monto": monto,
                "tipo": "TRANSFERENCIA"
            }],
            "hash_anterior": ultimo_bloque["hash"],
            "hash": hashlib.sha256(f"{emisor}{receptor}{monto}{time.time()}".encode()).hexdigest()
        }
        
        blockchain.insert_one(nuevo_bloque)
        return jsonify({"status": "ok", "mensaje": "Transferencia exitosa"}), 200

    except ecdsa.BadSignatureError:
        return jsonify({"status": "error", "mensaje": "Firma inválida. ¡Intento de fraude!"}), 401
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
        
@app.route('/minar', methods=['POST'])
def recibir_bloque():
    datos = request.json
    direccion = datos.get("wallet")
    nonce = datos.get("nonce")
    
    contenido = f"{direccion}{nonce}".encode()
    h = hashlib.sha256(contenido).hexdigest()
    
    if h.startswith("0" * DIFICULTAD):
        try:
            ultimo = list(blockchain.find().sort("indice", -1).limit(1))[0]
            nuevo_bloque = {
                "indice": ultimo["indice"] + 1,
                "timestamp": time.time(),
                "transacciones": [{
                    "emisor": "SISTEMA", 
                    "receptor": direccion, 
                    "monto": RECOMPENSA_MINADO, 
                    "tipo": "MINADO"
                }],
                "hash_anterior": ultimo["hash"],
                "nonce": nonce,
                "hash": h
            }
            blockchain.insert_one(nuevo_bloque)
            return jsonify({"status": "ok", "mensaje": "Bloque minado"}), 200
        except Exception as e:
            return jsonify({"status": "error", "mensaje": str(e)}), 500
    return jsonify({"status": "error", "mensaje": "Dificultad baja"}), 400

@app.route('/transferir', methods=['POST'])
def transferir():
    datos = request.json
    emisor = datos.get("emisor")
    receptor = datos.get("receptor")
    monto = float(datos.get("monto"))
    firma = datos.get("firma")

    # 1. Verificar firma
    mensaje = f"{emisor}{receptor}{monto}"
    if not verificar_firma(emisor, mensaje, firma):
        return jsonify({"status": "error", "mensaje": "Firma digital inválida"}), 401

    # 2. Verificar saldo
    if obtener_saldo(emisor) < monto:
        return jsonify({"status": "error", "mensaje": "Saldo insuficiente"}), 400

    # 3. Registrar transacción en un nuevo bloque
    try:
        ultimo = list(blockchain.find().sort("indice", -1).limit(1))[0]
        nuevo_bloque = {
            "indice": ultimo["indice"] + 1,
            "timestamp": time.time(),
            "transacciones": [{
                "emisor": emisor, 
                "receptor": receptor, 
                "monto": monto, 
                "tipo": "TRANSFERENCIA"
            }],
            "hash_anterior": ultimo["hash"],
            "nonce": 0, # Las transacciones no requieren minado forzoso aquí
            "hash": hashlib.sha256(f"{emisor}{receptor}{monto}{time.time()}".encode()).hexdigest()
        }
        blockchain.insert_one(nuevo_bloque)
        return jsonify({"status": "ok", "mensaje": "Transferencia exitosa"}), 200
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route('/cadena', methods=['GET'])
def ver_cadena():
    datos = list(blockchain.find({}, {"_id": 0}))
    return jsonify(datos), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
