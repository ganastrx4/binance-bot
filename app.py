import hashlib
import json
import time
from flask import Flask, request, jsonify, render_template_string
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
# 🎨 DISEÑO DE LA INTERFAZ (HTML/CSS)
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <title>CharlyCoin Node | Chimalhuacán</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0f0f0f; color: #00ff00; font-family: 'Courier New', monospace; }
        .card { background: #1a1a1a; border: 1px solid #00ff00; color: #00ff00; margin-top: 20px; }
        .btn-custom { background: #00ff00; color: #000; font-weight: bold; }
        .stats { font-size: 1.2rem; }
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="text-center mb-5">
            <h1>🚀 CHARLYCOIN BCHC NODE</h1>
            <p>Estado: <span class="badge bg-success">OPERATIVO</span> | Red: Binance Smart Chain</p>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card p-4">
                    <h3>📊 Red</h3>
                    <p class="stats">Bloques: {{ bloques }}</p>
                    <p class="stats">Dificultad: {{ dificultad }}</p>
                    <p class="stats">Recompensa: {{ recompensa }} CHC</p>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card p-4">
                    <h3>🔗 Último Bloque</h3>
                    <div class="overflow-auto" style="max-height: 200px;">
                        <pre style="color: #00ff00;">{{ ultimo_bloque | tojson(indent=2) }}</pre>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-5 text-center">
            <a href="/cadena" class="btn btn-outline-success mx-2">Ver Cadena Completa</a>
            <button onclick="location.reload()" class="btn btn-custom mx-2">Actualizar Datos</button>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# 🧠 FUNCIONES BASE
# ==========================================
def calcular_hash(bloque):
    bloque_string = json.dumps(bloque, sort_keys=True).encode()
    return hashlib.sha256(bloque_string).hexdigest()

def crear_bloque_genesis():
    if not blockchain:
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
# 🌐 RUTAS DE NAVEGACIÓN
# ==========================================
@app.route("/")
def home():
    return render_template_string(
        HTML_INDEX, 
        bloques=len(blockchain), 
        dificultad=DIFICULTAD,
        recompensa=calcular_recompensa(),
        ultimo_bloque=blockchain[-1] if blockchain else {}
    )

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

@app.route("/cadena", methods=["GET"])
def ver_cadena():
    return jsonify(blockchain)

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

if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
