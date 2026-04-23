import hashlib
import json
import time
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN DE MONGODB
# ==========================================
MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
collection = db['blockchain']

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18
HALVING_CADA = 21000

# ==========================================
# 🎨 TU DISEÑO: CHARLYSCAN (HTML)
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Nodo MongoDB</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #070b14; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; }
        .neon-text { color: #00f2ff; text-shadow: 0 0 15px rgba(0, 242, 255, 0.6); }
        .mining-anim { animation: blink 1.5s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    </style>
</head>
<body class="p-4 md:p-10">
    <div class="max-w-6xl mx-auto">
        <header class="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
            <div>
                <h1 class="text-5xl font-black neon-text tracking-tighter">CHARLYSCAN</h1>
                <p class="text-slate-500 font-mono text-sm">Respaldo en MongoDB Cluster</p>
            </div>
            <div class="card p-4 flex items-center gap-4">
                <p id="total-blocks" class="text-2xl font-mono font-bold text-white">Bloques: ...</p>
            </div>
        </header>

        <div class="card p-8 mb-10 border-l-4 border-l-yellow-500 text-center">
            <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Suministro Total</h3>
            <p id="total-supply" class="text-5xl font-black text-yellow-400 font-mono">0 CHC</p>
        </div>

        <div class="card overflow-hidden">
            <div class="p-5 border-b border-slate-800 bg-slate-900/50">
                <h2 class="font-bold text-lg text-slate-200">Historial desde la Base de Datos</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-900/80 text-slate-500 text-xs uppercase">
                        <tr>
                            <th class="p-5">ID</th>
                            <th class="p-5">Minero</th>
                            <th class="p-5">Monto</th>
                            <th class="p-5">Hash</th>
                        </tr>
                    </thead>
                    <tbody id="blockchain-table" class="divide-y divide-slate-800">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/cadena');
                const chain = await response.json();
                let tableHtml = '';
                let supply = 0;
                [...chain].reverse().forEach(block => {
                    const tx = block.transacciones[0] || {receptor: "GENESIS", monto: 0};
                    supply += parseFloat(tx.monto);
                    tableHtml += `
                        <tr class="hover:bg-slate-800/40">
                            <td class="p-5 font-mono text-cyan-500 font-bold">#${block.indice}</td>
                            <td class="p-5 text-xs text-slate-400">${tx.receptor}</td>
                            <td class="p-5 font-black text-yellow-500">+${tx.monto}</td>
                            <td class="p-5 font-mono text-[10px] text-slate-600">${block.hash.substring(0,24)}...</td>
                        </tr>`;
                });
                document.getElementById('blockchain-table').innerHTML = tableHtml;
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);
                document.getElementById('total-supply').innerText = supply.toFixed(2) + ' CHC';
            } catch (e) {}
        }
        setInterval(updateDashboard, 5000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==========================================
# 🧠 LÓGICA DE BLOCKCHAIN CON MONGO
# ==========================================
def calcular_hash(bloque):
    bloque_copy = {k: v for k, v in bloque.items() if k != '_id' and k != 'hash'}
    bloque_string = json.dumps(bloque_copy, sort_keys=True).encode()
    return hashlib.sha256(bloque_string).hexdigest()

def crear_bloque_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0, "timestamp": time.time(), "transacciones": [],
            "nonce": 0, "hash_anterior": "0"
        }
        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

def calcular_recompensa():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    return max(RECOMPENSA_INICIAL / (2 ** halvings), 0.00000001)

# ==========================================
# 🌐 RUTAS
# ==========================================
@app.route("/")
def home():
    return render_template_string(HTML_INDEX)

@app.route("/minar", methods=["POST"])
def minar():
    data = request.json
    wallet, nonce = data.get("wallet"), data.get("nonce")
    
    hash_prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()
    if not hash_prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "Hash inválido"}), 400

    ultimo_bloque = collection.find_one(sort=[("indice", -1)])
    
    nuevo_bloque = {
        "indice": ultimo_bloque["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{"emisor": "RED", "receptor": wallet, "monto": calcular_recompensa()}],
        "nonce": nonce,
        "hash_anterior": ultimo_bloque["hash"]
    }
    nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
    
    collection.insert_one(nuevo_bloque)
    return jsonify({"mensaje": "Bloque guardado en MongoDB", "bloque": nuevo_bloque})

@app.route("/cadena", methods=["GET"])
def ver_cadena():
    # Convertimos los datos de Mongo a una lista JSON válida
    cadena = list(collection.find({}, {'_id': 0}))
    return jsonify(cadena)

if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
