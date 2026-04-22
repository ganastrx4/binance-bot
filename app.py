import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
import json

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN DE RED Y CONTRATOS
# ==========================================
# Si usas variables de entorno en Render, las tomará de ahí. 
# Si no, usará estas por defecto:
RPC_URL = "https://bsc-dataseed.binance.org/"
TOKEN_ADDRESS = os.getenv('TOKEN_ADDRESS', '0xf74c6721970CA2735401F78476327a3d8867e73b')
POOL_ADDRESS = os.getenv('POOL_ADDRESS', '0x02E309e567c1783B5b3a9c67D00d9393d0219412')
# Tu llave privada (Para que la Pool firme las transacciones)
PRIVATE_KEY = os.getenv('POOL_PRIVATE_KEY') 

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# ABI mínima para la función MINT del nuevo contrato
ABI_TOKEN = [
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# ==========================================
# 📊 BASE DE DATOS TEMPORAL (Tus 370k CHC)
# ==========================================
# Aquí es donde el servidor recuerda cuánto ha minado cada quien
# En producción, esto debería conectar con tu archivo JSON o SQL
saldos_mineros = {
    "global": 370460.0,
    # "0xTuBilletera": 1000.0 (Esto se llena con los POST /minar)
}

@app.route('/')
def home():
    return jsonify({
        "proyecto": "NewWorld Network - Chimalhuacán",
        "token": TOKEN_ADDRESS,
        "suministro_global": saldos_mineros["global"]
    })

# ==========================================
# 🚀 RUTA DE CANJE (EL PUENTE)
# ==========================================
@app.route('/canjear', methods=['POST'])
def canjear():
    datos = request.json
    user_wallet = datos.get('wallet')
    cantidad = float(datos.get('cantidad'))

    # 1. Validar si el usuario tiene saldo en el nodo
    # (Aquí deberías buscar en tu base de datos real)
    if saldos_mineros["global"] < cantidad:
        return jsonify({"mensaje": "Saldo insuficiente en el nodo"}), 400

    try:
        # 2. Preparar la transacción en Binance Smart Chain
        contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=ABI_TOKEN)
        
        # Convertir a formato blockchain (18 decimales)
        monto_wei = w3.to_wei(cantidad, 'ether')
        
        nonce = w3.eth.get_transaction_count(POOL_ADDRESS)
        
        tx = contract.functions.mint(user_wallet, monto_wei).build_transaction({
            'chainId': 56, # BSC Mainnet
            'gas': 100000,
            'gasPrice': w3.to_wei('3', 'gwei'),
            'nonce': nonce,
        })

        # 3. Firmar y Enviar
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # 4. Descontar del saldo del nodo para evitar duplicidad
        saldos_mineros["global"] -= cantidad
        
        return jsonify({
            "status": "Exito",
            "tx_hash": w3.to_hex(tx_hash),
            "mensaje": f"Se han enviado {cantidad} BCHC a tu billetera"
        })

    except Exception as e:
        return jsonify({"mensaje": f"Error en blockchain: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
