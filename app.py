import hashlib
import json
import time
import urllib.parse
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN DE MONGODB (SEGURA)
# ==========================================
password = urllib.parse.quote_plus("caseta82*") 
MONGO_URI = f"mongodb+srv://charly:{password}@cluster0.daebfm2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client['charlycoin_db']
collection = db['blockchain']

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18
HALVING_CADA = 21000

# ==========================================
# 🎨 TU DISEÑO ESPECTACULAR + CONVERSOR 0x
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Panel En Vivo</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-sha3/0.8.2/sha3.min.js"></script>
    <style>
        body { background: #070b14; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); }
        .neon-text { color: #00f2ff; text-shadow: 0 0 15px rgba(0, 242, 255, 0.6); }
        .neon-border:focus { border-color: #00f2ff; box-shadow: 0 0 10px rgba(0, 242, 255, 0.3); }
        .mining-anim { animation: blink 1.5s infinite; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #070b14; }
        ::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 10px; }
    </style>
</head>
<body class="p-4 md:p-10">
    <div class="max-w-6xl mx-auto">
        <header class="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
            <div>
                <h1 class="text-5xl font-black neon-text tracking-tighter">CHARLYSCAN</h1>
                <p class="text-slate-500 font-mono text-sm">Explorador de bloques para NewWorld Network</p>
            </div>
            <div class="card p-4 flex items-center gap-4">
                <div class="text-right">
                    <p class="text-xs text-slate-400 uppercase tracking-widest">Estado del Nodo</p>
                    <p class="text-green-400 font-bold flex items-center justify-end gap-2">
                        <span class="mining-anim">●</span> EN VIVO (MONGODB)
                    </p>
                </div>
                <div class="h-10 w-px bg-slate-700"></div>
                <div>
                    <p id="total-blocks" class="text-2xl font-mono font-bold text-white">Bloques: 0</p>
                </div>
            </div>
        </header>

        <div class="card p-6 mb-8 border-l-4 border-l-purple-500 bg-purple-900/5">
            <label class="block mb-3 text-sm font-semibold text-purple-300 uppercase tracking-tight">Convertidor de Billetera 0x (Exchange Compatible)</label>
            <div class="flex flex-col md:flex-row gap-4 items-center">
                <input type="text" id="long-hash-input" oninput="generate0x()" 
                       placeholder="Pega aquí tu hash largo de 128..." 
                       class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none neon-border text-xs text-slate-400 font-mono">
                <div class="w-full md:w-auto min-w-[300px] bg-black/80 p-4 rounded-xl border border-purple-900/50 flex justify-between items-center">
                    <span class="text-[10px] text-slate-500 font-bold uppercase mr-2">Wallet 0x:</span>
                    <span id="result-0x" class="text-green-400 font-mono font-bold text-sm">---</span>
                </div>
            </div>
        </div>

        <div class="card p-6 mb-8 border-l-4 border-l-cyan-500">
            <label class="block mb-3 text-sm font-semibold text-slate-300">Consultar Saldo (Soporta Hash Largo y 0x)</label>
            <div class="flex gap-2">
                <input type="text" id="wallet-input" 
                       placeholder="Ingresa tu dirección y pulsa Enter..." 
                       class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none neon-border text-cyan-400 font-mono transition-all">
                <button onclick="updateDashboard()" class="bg-cyan-600 hover:bg-cyan-500 px-6 rounded-xl font-bold transition-colors">
                    BUSCAR
                </button>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="card p-8 bg-gradient-to-br from-gray-900 to-black border-l-4 border-l-yellow-500">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Mi Saldo Acumulado</h3>
                <p id="user-balance" class="text-4xl font-black text-yellow-400 font-mono">0.00 CHC</p>
                <p class="text-slate-500 text-xs mt-2">Basado en bloques validados</p>
            </div>
            <div class="card p-8 bg-gradient-to-br from-gray-900 to-black">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Suministro en Circulación</h3>
                <p id="total-supply" class="text-4xl font-black text-white font-mono">0 CHC</p>
                <p class="text-slate-500 text-xs mt-2">Límite: 21,000,000,000 CHC</p>
            </div>
            <div class="card p-8 bg-gradient-to-br from-gray-900 to-black border-dashed border-slate-700">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Dificultad de Red</h3>
                <p class="text-4xl font-black text-purple-500 font-mono">5 ZEROS</p>
                <p class="text-slate-500 text-xs mt-2">Hash Rate: Estable</p>
            </div>
        </div>

        <div class="card overflow-hidden">
            <div class="p-5 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
                <h2 class="font-bold text-lg text-slate-200">Historial Reciente de la Blockchain</h2>
                <span class="text-xs text-slate-500 tracking-tighter">NODO MAESTRO: RENDER CLOUD</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-900/80 text-slate-500 text-xs uppercase">
                        <tr>
                            <th class="p-5">ID Bloque</th>
                            <th class="p-5">Identidad (0x) / Original</th>
                            <th class="p-5">Monto (CHC)</th>
                            <th class="p-5">Firma (Hash)</th>
                        </tr>
                    </thead>
                    <tbody id="blockchain-table" class="divide-y divide-slate-800"></tbody>
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
                const response = await fetch(window.location.origin + '/cadena');
                const chain = await response.json();
                const myWallet = document.getElementById('wallet-input').value.trim().toLowerCase();
                
                let userBalance = 0, totalSupply = 0, tableHtml = '';

                [...chain].reverse().forEach(block => {
                    const tx = block.transacciones[0] || {receptor: "SISTEMA", monto: 0};
                    const monto = parseFloat(tx.monto);
                    totalSupply += monto;
                    
                    const derived0x = generate0x(tx.receptor);

                    if(myWallet !== "" && (tx.receptor.toLowerCase() === myWallet || (derived0x && derived0x.toLowerCase() === myWallet))) {
                        userBalance += monto;
                    }

                    tableHtml += `
                        <tr class="hover:bg-slate-800/40 transition-all group">
                            <td class="p-5 font-mono text-cyan-500 font-bold text-lg">#${block.indice}</td>
                            <td class="p-5">
                                <div class="flex flex-col">
                                    <span class="text-green-400 font-bold text-xs">${derived0x || 'N/A'}</span>
                                    <span class="font-mono text-[9px] text-slate-600 truncate max-w-[200px]">${tx.receptor}</span>
                                </div>
                            </td>
                            <td class="p-5 font-black text-yellow-500">+${monto.toLocaleString()}</td>
                            <td class="p-5 font-mono text-[10px] text-slate-600">${block.hash.substring(0,24)}...</td>
                        </tr>`;
                });

                document.getElementById('blockchain-table').innerHTML = tableHtml || '<tr><td colspan="4" class="p-10 text-center text-slate-500">Conectando con base de datos...</td></tr>';
                document.getElementById('user-balance').innerText = userBalance.toLocaleString(undefined, {minimumFractionDigits: 2}) + ' CHC';
                document.getElementById('total-supply').innerText = totalSupply.toLocaleString() + ' CHC';
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);

            } catch (err) { console.error(err); }
        }

        document.getElementById('wallet-input').addEventListener('keypress', (e) => e.key === 'Enter' && updateDashboard());
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
