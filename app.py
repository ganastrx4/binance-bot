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

# ==========================================
# 🎨 TU DISEÑO: CHARLYSCAN (Directo en el código)
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Panel En Vivo</title>
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
                <p class="text-slate-500 font-mono text-sm">Explorador de bloques para NewWorld Network</p>
            </div>
            <div class="card p-4 flex items-center gap-4">
                <div class="text-right">
                    <p class="text-xs text-slate-400 uppercase tracking-widest">Estado del Nodo</p>
                    <p class="text-green-400 font-bold flex items-center justify-end gap-2">
                        <span class="mining-anim">●</span> EN VIVO (RENDER)
                    </p>
                </div>
                <div class="h-10 w-px bg-slate-700"></div>
                <div>
                    <p id="total-blocks" class="text-2xl font-mono font-bold text-white">Bloques: 0</p>
                </div>
            </div>
        </header>

        <div class="card p-6 mb-8 border-l-4 border-l-cyan-500">
            <label class="block mb-3 text-sm font-semibold text-slate-300">Rastreador de Minería Personal</label>
            <div class="flex gap-2">
                <input type="text" id="wallet-input" 
                       placeholder="Pega aquí tu dirección pública (Wallet)..." 
                       class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none text-cyan-400 font-mono">
                <button onclick="updateDashboard()" class="bg-cyan-600 hover:bg-cyan-500 px-6 rounded-xl font-bold transition-colors">
                    BUSCAR
                </button>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="card p-8 border-l-4 border-l-yellow-500">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Mi Saldo Acumulado</h3>
                <p id="user-balance" class="text-4xl font-black text-yellow-400 font-mono">0.00 CHC</p>
            </div>
            <div class="card p-8">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Suministro Total</h3>
                <p id="total-supply" class="text-4xl font-black text-white font-mono">0 CHC</p>
            </div>
            <div class="card p-8 border-dashed border-slate-700">
                <h3 class="text-slate-400 text-xs font-bold uppercase mb-4 tracking-widest">Dificultad</h3>
                <p class="text-4xl font-black text-purple-500 font-mono">5 ZEROS</p>
            </div>
        </div>

        <div class="card overflow-hidden">
            <div class="p-5 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
                <h2 class="font-bold text-lg text-slate-200">Historial Reciente de la Blockchain</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-slate-900/80 text-slate-500 text-xs uppercase">
                        <tr>
                            <th class="p-5">ID Bloque</th>
                            <th class="p-5">Minero (Receptor)</th>
                            <th class="p-5">Monto (CHC)</th>
                            <th class="p-5">Firma (Hash)</th>
                        </tr>
                    </thead>
                    <tbody id="blockchain-table" class="divide-y divide-slate-800">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin + '/cadena';

        async function updateDashboard() {
            try {
                const response = await fetch(API_URL);
                const chain = await response.json();
                const myWallet = document.getElementById('wallet-input').value.trim();
                
                let userBalance = 0;
                let totalSupply = 0;
                let tableHtml = '';

                const recentBlocks = [...chain].reverse();

                recentBlocks.forEach(block => {
                    const tx = block.transacciones[0];
                    if(tx) {
                        const monto = parseFloat(tx.monto);
                        totalSupply += monto;
                        if(myWallet !== "" && tx.receptor === myWallet) userBalance += monto;

                        tableHtml += `
                            <tr class="hover:bg-slate-800/40">
                                <td class="p-5 font-mono text-cyan-500 font-bold">#${block.indice}</td>
                                <td class="p-5"><span class="font-mono text-xs text-slate-400">${tx.receptor}</span></td>
                                <td class="p-5 font-black text-yellow-500">+${monto.toFixed(2)}</td>
                                <td class="p-5 font-mono text-[10px] text-slate-600">${block.hash.substring(0,24)}...</td>
                            </tr>
                        `;
                    }
                });

                document.getElementById('blockchain-table').innerHTML = tableHtml;
                document.getElementById('user-balance').innerText = userBalance.toFixed(2) + ' CHC';
                document.getElementById('total-supply').innerText = totalSupply.toFixed(0) + ' CHC';
                document.getElementById('total-blocks').innerText = 'Bloques: ' + (chain.length - 1);
            } catch (err) {
                console.error("Error:", err);
            }
        }
        setInterval(updateDashboard, 5000);
        updateDashboard();
    </script>
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
            "indice": 0, "timestamp": time.time(), "transacciones": [],
            "nonce": 0, "hash_anterior": "0"
        }
        bloque["hash"] = calcular_hash(bloque)
        blockchain.append(bloque)

def calcular_recompensa():
    bloques = len(blockchain)
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
    wallet = data.get("wallet")
    nonce = data.get("nonce")
    if not wallet: return jsonify({"error": "Falta wallet"}), 400

    hash_prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()
    if not hash_prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "Prueba fallida"}), 400

    nuevo_bloque = {
        "indice": len(blockchain),
        "timestamp": time.time(),
        "transacciones": [{"emisor": "RED", "receptor": wallet, "monto": calcular_recompensa()}],
        "nonce": nonce,
        "hash_anterior": blockchain[-1]["hash"]
    }
    nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
    blockchain.append(nuevo_bloque)
    return jsonify({"mensaje": "Minado OK", "bloque": nuevo_bloque})

@app.route("/cadena", methods=["GET"])
def ver_cadena():
    return jsonify(blockchain)

if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
