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
# 🎨 DISEÑO: CHARLYSCAN TOTAL
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Nodo Maestro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-sha3/0.8.2/sha3.min.js"></script>
    <style>
        body { background: #070b14; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; }
        .neon-text { color: #00f2ff; text-shadow: 0 0 15px rgba(0, 242, 255, 0.6); }
        .neon-border:focus { border-color: #00f2ff; box-shadow: 0 0 10px rgba(0, 242, 255, 0.2); }
    </style>
</head>
<body class="p-4 md:p-10">
    <div class="max-w-6xl mx-auto">
        
        <header class="flex flex-col md:flex-row justify-between items-center mb-10 gap-4 text-center md:text-left">
            <div>
                <h1 class="text-5xl font-black neon-text tracking-tighter">CHARLYSCAN</h1>
                <p class="text-slate-500 font-mono text-sm uppercase tracking-widest">NewWorld Network | MongoDB</p>
            </div>
            <div class="card p-4 flex items-center gap-4">
                <p id="total-blocks" class="text-2xl font-mono font-bold text-cyan-400">Bloques: 0</p>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            <div class="card p-6 border-l-4 border-l-purple-500">
                <h3 class="text-slate-400 text-xs font-bold mb-4 uppercase">Convertidor a Wallet 0x</h3>
                <input type="text" id="long-hash-input" oninput="generate0x()" placeholder="Pega hash de 128 aquí..." 
                       class="w-full bg-black/50 border border-slate-700 p-3 rounded-lg focus:outline-none neon-border text-xs font-mono mb-4">
                <div class="bg-black/80 p-3 rounded border border-slate-800">
                    <p class="text-[9px] text-slate-500 uppercase">Dirección Compatible:</p>
                    <p id="result-0x" class="text-purple-400 font-mono font-bold text-sm break-all">---</p>
                </div>
            </div>

            <div class="card p-6 border-l-4 border-l-cyan-500">
                <h3 class="text-slate-400 text-xs font-bold mb-4 uppercase">Buscador y Suministro</h3>
                <div class="flex gap-2 mb-4">
                    <input type="text" id="search-input" placeholder="0x... o Hash Largo" 
                           class="flex-1 bg-black/50 border border-slate-700 p-3 rounded-lg focus:outline-none neon-border text-cyan-400 font-mono text-sm">
                    <button onclick="updateDashboard()" class="bg-cyan-600 hover:bg-cyan-500 px-4 rounded-lg font-bold">BUSCAR</button>
                </div>
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-[9px] text-slate-500 uppercase">Tu Saldo:</p>
                        <p id="user-balance" class="text-2xl font-black text-yellow-400 font-mono">0.00 CHC</p>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] text-slate-500 uppercase">Suministro Total:</p>
                        <p id="total-supply" class="text-2xl font-black text-white font-mono">0 CHC</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card overflow-hidden">
            <div class="p-4 border-b border-slate-800 bg-slate-900/50">
                <h2 class="font-bold text-slate-200 uppercase text-xs">Historial de Bloques</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-900 text-slate-500 text-[10px] uppercase">
                        <tr>
                            <th class="p-4">ID</th>
                            <th class="p-4">Miner Wallet (0x)</th>
                            <th class="p-4 text-right">Monto</th>
                        </tr>
                    </thead>
                    <tbody id="blockchain-table" class="divide-y divide-slate-800 font-mono text-xs"></tbody>
                </table>
            </div>
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
                
                let balance = 0;
                let supply = 0;
                let tableHtml = '';

                [...chain].reverse().forEach(block => {
                    const tx = block.transacciones[0] || {receptor: "SISTEMA", monto: 0};
                    const monto = parseFloat(tx.monto);
                    supply += monto;
                    
                    const derived0x = generate0x(tx.receptor);

                    if (search !== "" && (tx.receptor.toLowerCase() === search || (derived0x && derived0x.toLowerCase() === search))) {
                        balance += monto;
                    }

                    tableHtml += `
                        <tr class="hover:bg-slate-800/40">
                            <td class="p-4 text-cyan-500 font-bold">#${block.indice}</td>
                            <td class="p-4 text-slate-400">
                                <span class="block text-[8px] opacity-50">${tx.receptor}</span>
                                <span class="text-green-400 font-bold">${derived0x || '0x000...'}</span>
                            </td>
                            <td class="p-4 text-right font-black text-yellow-500">+${monto.toFixed(2)}</td>
                        </tr>
                    `;
                });

                document.getElementById('blockchain-table').innerHTML = tableHtml;
                document.getElementById('user-balance').innerText = balance.toLocaleString() + ' CHC';
                document.getElementById('total-supply').innerText = supply.toLocaleString() + ' CHC';
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);
            } catch (e) { console.log(e); }
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
