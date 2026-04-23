import hashlib
import json
import time
import urllib.parse  # Importante para manejar el '*' de tu clave
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN DE MONGODB (CORREGIDA)
# ==========================================
# Tu contraseña tiene un '*', hay que "traducirlo" para que Python no se confunda
password = urllib.parse.quote_plus("caseta82*") 
MONGO_URI = f"mongodb+srv://charly:{password}@cluster0.daebfm2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['charlycoin_db']
    collection = db['blockchain']
    # Prueba de conexión rápida
    client.admin.command('ping')
    print("✅ CONECTADO EXITOSAMENTE A MONGODB")
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN: {e}")

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18
HALVING_CADA = 21000

# ==========================================
# 🎨 DISEÑO: CHARLYSCAN (RESTAURADO COMPLETO)
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Realtime</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-sha3/0.8.2/sha3.min.js"></script>
    <style>
        body { background: #020617; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
        .neon-text { color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.4); }
    </style>
</head>
<body class="p-6">
    <div class="max-w-5xl mx-auto">
        <header class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-black neon-text italic">CHARLYSCAN</h1>
            <div class="bg-slate-800 px-4 py-2 rounded-full border border-slate-700">
                <span id="total-blocks" class="font-mono text-cyan-400 font-bold">Cargando bloques...</span>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="card p-5">
                <h2 class="text-xs font-bold text-slate-500 uppercase mb-3">Convertidor de Wallet</h2>
                <input type="text" id="long-hash-input" oninput="generate0x()" placeholder="Pega hash de 128..." 
                       class="w-full bg-slate-950 border border-slate-800 p-3 rounded text-[10px] font-mono mb-3 focus:border-cyan-500 outline-none">
                <div class="p-3 bg-slate-950 rounded border border-slate-900">
                    <p class="text-[9px] text-slate-600 uppercase mb-1">Dirección 0x (Exchange):</p>
                    <p id="result-0x" class="text-green-400 font-mono text-xs break-all">---</p>
                </div>
            </div>

            <div class="card p-5 border-t-4 border-t-cyan-500">
                <div class="flex gap-2 mb-4">
                    <input type="text" id="search-input" placeholder="Buscar 0x o Hash..." 
                           class="flex-1 bg-slate-950 border border-slate-800 p-2 rounded text-xs font-mono outline-none">
                    <button onclick="updateDashboard()" class="bg-cyan-600 px-4 rounded text-xs font-bold uppercase tracking-widest">OK</button>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <p class="text-[9px] text-slate-500 uppercase">Mi Saldo</p>
                        <p id="user-balance" class="text-xl font-black text-yellow-500">0.00</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] text-slate-500 uppercase">Suministro Total</p>
                        <p id="total-supply" class="text-xl font-black text-white">0.00</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card overflow-hidden">
            <table class="w-full text-left">
                <thead class="bg-slate-800/50 text-[10px] text-slate-400 uppercase">
                    <tr>
                        <th class="p-4">Bloque</th>
                        <th class="p-4">Minero (Identidad 0x)</th>
                        <th class="p-4 text-right">CHC</th>
                    </tr>
                </thead>
                <tbody id="blockchain-table" class="divide-y divide-slate-800 font-mono text-[11px]"></tbody>
            </table>
        </div>
    </div>

    <script>
        function generate0x(hash = null) {
            const input = hash || document.getElementById('long-hash-input').value.trim();
            if (input.length > 20) {
                const keccak = keccak256(input);
                const wallet0x = "0x" + keccak.substring(keccak.length - 40);
                if (!hash) document.getElementById('result-0x').innerText = wallet0x;
                return wallet0x;
            }
            return null;
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/cadena');
                const chain = await response.json();
                const search = document.getElementById('search-input').value.trim().toLowerCase();
                
                let balance = 0, supply = 0, tableHtml = '';

                [...chain].reverse().forEach(block => {
                    const tx = block.transacciones[0] || {receptor: "GENESIS", monto: 0};
                    const monto = parseFloat(tx.monto);
                    supply += monto;
                    const derived0x = generate0x(tx.receptor);

                    if (search !== "" && (tx.receptor.toLowerCase() === search || (derived0x && derived0x.toLowerCase() === search))) {
                        balance += monto;
                    }

                    tableHtml += `
                        <tr class="hover:bg-slate-800/20">
                            <td class="p-4 text-cyan-500">#${block.indice}</td>
                            <td class="p-4">
                                <span class="block text-[8px] opacity-40 break-all">${tx.receptor}</span>
                                <span class="text-green-500 font-bold">${derived0x || '0x00...'}</span>
                            </td>
                            <td class="p-4 text-right font-bold text-yellow-500">+${monto.toFixed(2)}</td>
                        </tr>`;
                });

                document.getElementById('blockchain-table').innerHTML = tableHtml;
                document.getElementById('user-balance').innerText = balance.toFixed(2) + ' CHC';
                document.getElementById('total-supply').innerText = supply.toFixed(2) + ' CHC';
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);
            } catch (e) { console.error(e); }
        }
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==========================================
# 🧠 BACKEND (MONGODB)
# ==========================================
def calcular_hash(bloque):
    bloque_copy = {k: v for k, v in bloque.items() if k != '_id' and k != 'hash'}
    bloque_string = json.dumps(bloque_copy, sort_keys=True).encode()
    return hashlib.sha256(bloque_string).hexdigest()

def crear_bloque_genesis():
    if collection.count_documents({}) == 0:
        bloque = {"indice": 0, "timestamp": time.time(), "transacciones": [], "nonce": 0, "hash_anterior": "0"}
        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

def calcular_recompensa():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    return max(RECOMPENSA_INICIAL / (2 ** halvings), 0.00000001)

@app.route("/")
def home():
    return render_template_string(HTML_INDEX)

@app.route("/minar", methods=["POST"])
def minar():
    data = request.json
    wallet, nonce = data.get("wallet"), data.get("nonce")
    hash_prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()
    if not hash_prueba.startswith("0" * DIFICULTAD): return jsonify({"error": "Hash inválido"}), 400

    ultimo_bloque = collection.find_one(sort=[("indice", -1)])
    recompensa = calcular_recompensa()
    
    nuevo_bloque = {
        "indice": ultimo_bloque["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{"emisor": "RED", "receptor": wallet, "monto": recompensa}],
        "nonce": nonce,
        "hash_anterior": ultimo_bloque["hash"]
    }
    nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
    collection.insert_one(nuevo_bloque)
    return jsonify({"mensaje": "OK", "bloque": nuevo_bloque, "recompensa": recompensa})

@app.route("/cadena", methods=["GET"])
def ver_cadena():
    return jsonify(list(collection.find({}, {'_id': 0})))

if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
