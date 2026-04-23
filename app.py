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
# 🎨 DISEÑO: CHARLYSCAN CON CONVERSOR 0x
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Conversor de Billeteras</title>
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
        
        <header class="flex justify-between items-center mb-10">
            <h1 class="text-4xl font-black neon-text tracking-tighter text-center md:text-left">CHARLYSCAN</h1>
            <div id="total-blocks" class="text-xl font-mono font-bold text-cyan-400">Bloques: 0</div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            <div class="card p-6 border-l-4 border-l-green-500">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Generador de Dirección 0x</h3>
                <input type="text" id="long-hash-input" oninput="generate0x()" 
                       placeholder="Pega aquí el hash largo de 128..." 
                       class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none neon-border text-xs text-slate-300 mb-4 font-mono">
                
                <div class="bg-black/80 p-4 rounded-lg border border-slate-800">
                    <p class="text-[10px] text-slate-500 uppercase mb-1">Tu Wallet Compatible (0x):</p>
                    <p id="result-0x" class="text-green-400 font-mono font-bold text-sm md:text-base break-all">---</p>
                </div>
            </div>

            <div class="card p-6 border-l-4 border-l-cyan-500">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Consultar Saldo Red CHC</h3>
                <div class="flex gap-2">
                    <input type="text" id="search-input" placeholder="0x... o Hash Largo" 
                           class="flex-1 bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none neon-border text-cyan-400 font-mono">
                    <button onclick="updateDashboard()" class="bg-cyan-600 hover:bg-cyan-500 px-6 rounded-xl font-bold">BUSCAR</button>
                </div>
                <p id="user-balance" class="mt-4 text-3xl font-black text-yellow-400 font-mono text-center">0.00 CHC</p>
            </div>
        </div>

        <div class="card overflow-hidden">
            <div class="p-5 border-b border-slate-800 bg-slate-900/50">
                <h2 class="font-bold text-lg text-slate-200 uppercase tracking-widest text-xs">Transacciones de Red</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-900 text-slate-500 text-xs font-mono uppercase">
                        <tr>
                            <th class="p-5">Bloque</th>
                            <th class="p-5">Billetera (Convertida)</th>
                            <th class="p-5 text-right">Monto</th>
                        </tr>
                    </thead>
                    <tbody id="blockchain-table" class="divide-y divide-slate-800 font-mono text-sm"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Función para convertir el Hash Largo en una Dirección 0x (Estándar Ethereum/BSC)
        function generate0x(hash = null) {
            const input = hash || document.getElementById('long-hash-input').value.trim();
            const resultBox = document.getElementById('result-0x');
            
            if (input.length > 20) {
                // Usamos Keccak256 (el estándar de Ethereum) para derivar la dirección
                const keccak = keccak256(input);
                const wallet0x = "0x" + keccak.substring(keccak.length - 40);
                
                if (!hash) resultBox.innerText = wallet0x;
                return wallet0x;
            }
            if (!hash) resultBox.innerText = "---";
            return null;
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/cadena');
                const chain = await response.json();
                const search = document.getElementById('search-input').value.trim().toLowerCase();
                
                let balance = 0;
                let tableHtml = '';

                [...chain].reverse().forEach(block => {
                    const tx = block.transacciones[0] || {receptor: "GENESIS", monto: 0};
                    const monto = parseFloat(tx.monto);
                    
                    // Derivamos la dirección 0x para esta transacción
                    const derived0x = generate0x(tx.receptor);

                    if (search !== "" && (tx.receptor.toLowerCase() === search || (derived0x && derived0x.toLowerCase() === search))) {
                        balance += monto;
                    }

                    tableHtml += `
                        <tr class="hover:bg-slate-800/40">
                            <td class="p-5 text-cyan-500 font-bold">#${block.indice}</td>
                            <td class="p-5">
                                <div class="flex flex-col">
                                    <span class="text-[10px] text-slate-500 break-all mb-1">${tx.receptor}</span>
                                    <span class="text-xs text-green-400 font-bold">${derived0x || 'N/A'}</span>
                                </div>
                            </td>
                            <td class="p-5 text-right font-black text-yellow-500">+${monto.toFixed(2)}</td>
                        </tr>
                    `;
                });

                document.getElementById('blockchain-table').innerHTML = tableHtml;
                document.getElementById('user-balance').innerText = balance.toLocaleString() + ' CHC';
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);
            } catch (e) { console.error(e); }
        }

        setInterval(updateDashboard, 15000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==========================================
# 🧠 BACKEND LÓGICA (MONGODB)
# ==========================================
# (Se mantiene igual para asegurar compatibilidad con tus datos en la nube)
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
