import os
import json
import time
import hashlib
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import DuplicateKeyError

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIG
# ==========================================
PORT = int(os.environ.get("PORT", 10000))
MONGO_URI = os.environ.get("MONGO_URI", "").strip()

if MONGO_URI == "":
    MONGO_URI = "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&tls=true"

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000
MAX_SUPPLY = 21000000000 # El límite que querías mostrar

ULTIMO_MINADO = {}

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client["charlycoin_db"]
collection = db["blockchain"]

# Índices para que no se trabe
collection.create_index("hash")
try:
    collection.create_index([("indice", ASCENDING)], unique=True)
except:
    pass
# ==========================================
# consultar_saldo
# ==========================================

@app.route("/consultar_saldo", methods=["POST"])
def consultar_saldo():
    wallet = request.json["wallet"]

    usuario = db.wallets.find_one({"wallet": wallet})

    if not usuario:
        return jsonify({
            "success": False,
            "message": "Wallet no encontrada"
        })

    return jsonify({
        "success": True,
        "saldo_chc": usuario["saldo"],
        "canjeado": usuario.get("canjeado", False)
    })

# ==========================================
# HTML (CON FIX DE SUPPLY Y LÍMITE)
# ==========================================
@app.route("/swap_chc_to_chorox", methods=["POST"])
def swap():
    wallet = request.json["wallet"]

    usuario = db.wallets.find_one({"wallet": wallet})

    if usuario.get("canjeado"):
        return jsonify({
            "success": False,
            "message": "CHC ya intercambiados"
        })

    db.wallets.update_one(
        {"wallet": wallet},
        {"$set": {"canjeado": True}}
    )

    return jsonify({
        "success": True,
        "message": "Swap aprobado"
    })

# ==========================================
# HTML (CON FIX DE SUPPLY Y LÍMITE)
# ==========================================
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CharlyScan - Full Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background:#070b14; color:#f8fafc; font-family:Segoe UI; }
        .card { background:#111827; border:1px solid #1f2937; border-radius:16px; }
        .neon { color:#00f2ff; text-shadow:0 0 15px rgba(0,242,255,.6); }
        .blink { animation:blink 1.5s infinite; }
        @keyframes blink { 0%{opacity:1} 50%{opacity:.3} 100%{opacity:1} }
    </style>
</head>
<body class="p-6">
<div class="max-w-6xl mx-auto">
    <div class="flex justify-between items-center mb-8">
        <div>
            <h1 class="text-5xl font-black neon">CHARLYSCAN</h1>
            <p class="text-gray-400">Explorador Blockchain PRO</p>
        </div>
        <div class="card p-4 text-right">
            <p class="text-sm text-gray-400">Estado Nodo</p>
            <p class="text-green-400 font-bold blink">● EN VIVO</p>
            <p id="total-blocks" class="text-xl mt-2 font-mono">Bloques: 0</p>
        </div>
    </div>

    <div class="card p-6 mb-6 border-l-4 border-cyan-500">
        <p class="text-sm text-gray-400 mb-2 font-bold uppercase tracking-widest">Wallet Tracker</p>
        <div class="flex gap-2">
            <input id="wallet-input" class="w-full p-3 bg-black border border-gray-700 rounded text-cyan-300 font-mono" placeholder="Ingresa tu dirección pública..." />
            <button onclick="updateDashboard()" class="bg-cyan-600 hover:bg-cyan-500 px-8 rounded font-bold transition-all">BUSCAR</button>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="card p-5 border-l-4 border-yellow-500">
            <p class="text-gray-400 text-xs font-bold uppercase">Mi Saldo</p>
            <p id="user-balance" class="text-3xl text-yellow-400 font-black font-mono">0.00 CHC</p>
        </div>
        <div class="card p-5 border-l-4 border-white">
            <p class="text-gray-400 text-xs font-bold uppercase">Suministro Actual</p>
            <p id="total-supply" class="text-3xl font-black font-mono text-white">0 CHC</p>
            <p class="text-gray-500 text-[10px] mt-1">MÁXIMO: 21,000,000,000 CHC</p>
        </div>
        <div class="card p-5 border-l-4 border-purple-500">
            <p class="text-gray-400 text-xs font-bold uppercase">Recompensa x Bloque</p>
            <p id="last-reward" class="text-3xl text-purple-400 font-black font-mono">0 CHC</p>
        </div>
    </div>

    <div class="card overflow-hidden">
        <div class="p-4 border-b border-gray-800 bg-gray-900/50">
            <h2 class="font-bold">Blockchain Explorer</h2>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead class="text-gray-500 text-xs uppercase bg-black/30">
                    <tr>
                        <th class="p-3">Bloque</th>
                        <th class="p-3">Minero</th>
                        <th class="p-3">Monto</th>
                        <th class="p-3">Hash</th>
                    </tr>
                </thead>
                <tbody id="blockchain-table" class="text-sm"></tbody>
            </table>
        </div>
    </div>
</div>

<script>
async function updateDashboard() {
    try {
        const wallet = document.getElementById('wallet-input').value.trim();
        const [chainRes, statsRes] = await Promise.all([
            fetch('/cadena'),
            fetch('/stats')
        ]);

        const chain = await chainRes.json();
        const stats = await statsRes.json();

        let tableHtml = "";
        chain.forEach(block => {
            const tx = block.transacciones?.[0];
            if (!tx) return;
            tableHtml += `
            <tr class="border-t border-gray-800 hover:bg-gray-900/50">
                <td class="p-3 text-cyan-400 font-bold">#${block.indice}</td>
                <td class="p-3 text-xs font-mono text-gray-400">${tx.receptor}</td>
                <td class="p-3 text-yellow-400 font-bold">+${tx.monto.toLocaleString()}</td>
                <td class="p-3 text-[10px] text-gray-600 font-mono">${block.hash.substring(0,24)}...</td>
            </tr>`;
        });

        document.getElementById("blockchain-table").innerHTML = tableHtml;
        document.getElementById("total-blocks").innerText = "Bloques: " + stats.bloques;
        
        // AQUÍ ESTABA EL ERROR: Usar stats.supply en lugar de stats.recompensa
        document.getElementById("total-supply").innerText = stats.supply.toLocaleString() + " CHC";
        document.getElementById("last-reward").innerText = stats.recompensa + " CHC";

        if(wallet !== ""){
            const balRes = await fetch("/balance/" + wallet);
            const bal = await balRes.json();
            document.getElementById("user-balance").innerText = bal.balance.toLocaleString(undefined, {minimumFractionDigits: 2}) + " CHC";
        }
    } catch(e){ console.log("Error:", e); }
}
setInterval(updateDashboard, 10000);
updateDashboard();
</script>
</body>
</html>
"""

# ==========================================
# LÓGICA DE SERVIDOR (MANTENIDA)
# ==========================================
def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)
    texto = json.dumps(copia, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()

def crear_genesis():
    if collection.count_documents({}) == 0:
        bloque = {"indice": 0, "timestamp": time.time(), "transacciones": [], "nonce": "0", "hash_anterior": "0"}
        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    return max(RECOMPENSA_INICIAL / (2 ** halvings), 0.00000001)

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/stats")
def stats():
    total = collection.count_documents({})
    pipeline = [{"$unwind": "$transacciones"}, {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}]
    result = list(collection.aggregate(pipeline))
    supply = result[0]["total"] if result else 0
    return jsonify({
        "bloques": max(total - 1, 0),
        "supply": round(supply, 2),
        "recompensa": recompensa_actual(),
        "dificultad": DIFICULTAD
    })

@app.route("/cadena")
def cadena():
    return jsonify(list(collection.find({}, {"_id": 0}).sort("indice", DESCENDING).limit(50)))

@app.route("/balance/<wallet>")
def balance(wallet):
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]
    res = list(collection.aggregate(pipeline))
    return jsonify({"wallet": wallet, "balance": res[0]["total"] if res else 0})

@app.route("/minar", methods=["POST"])
def minar():
    data = request.get_json(force=True)
    wallet = str(data.get("wallet", "")).strip()
    nonce = str(data.get("nonce", "")).strip()
    if not wallet or not nonce: return jsonify({"error": "datos incompletos"}), 400
    
    # Anti-spam simple
    ahora = time.time()
    if wallet in ULTIMO_MINADO and ahora - ULTIMO_MINADO[wallet] < 2:
        return jsonify({"error": "espera 2 seg"}), 429

    prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()
    if not prueba.startswith("0" * DIFICULTAD): return jsonify({"error": "hash invalido"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])
    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": ahora,
        "transacciones": [{"emisor": "RED", "receptor": wallet, "monto": recompensa_actual()}],
        "nonce": nonce,
        "hash_anterior": ultimo["hash"]
    }
    nuevo["hash"] = calcular_hash(nuevo)
    
    try:
        collection.insert_one(nuevo)
        ULTIMO_MINADO[wallet] = ahora
        return jsonify({"ok": True, "bloque": nuevo["indice"]})
    except:
        return jsonify({"error": "error de red"}), 500

if __name__ == "__main__":
    crear_genesis()
    app.run(host="0.0.0.0", port=PORT)
