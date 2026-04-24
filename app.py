# ==========================================
# 🚀 CHARLYCOIN NODE FULL PRO DEFINITIVO
# Render + MongoDB + Anti Crash + Fast Chain
# Archivo: app.py
# ==========================================

import os
import json
import time
import hashlib
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import DuplicateKeyError

# ==========================================
# APP
# ==========================================
app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIG
# ==========================================
PORT = int(os.environ.get("PORT", 10000))

MONGO_URI = os.environ.get("MONGO_URI", "").strip()

if MONGO_URI == "":
    print("⚠️ MONGO_URI no encontrada, usando respaldo")
    MONGO_URI = "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&tls=true"

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000

ULTIMO_MINADO = {}

# ==========================================
# MONGO
# ==========================================
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=30000,
    connectTimeoutMS=30000,
    socketTimeoutMS=30000,
    retryWrites=True
)

db = client["charlycoin_db"]
collection = db["blockchain"]

# ==========================================
# INDICES SEGUROS (ANTI ERROR DUPLICADOS)
# ==========================================
collection.create_index("hash")

try:
    collection.create_index([("indice", ASCENDING)], unique=True)
    print("✅ índice unique activo")
except:
    print("⚠️ índices duplicados detectados, usando índice normal")
    collection.create_index([("indice", ASCENDING)])

# ==========================================
# HTML
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

    <!-- HEADER -->
    <div class="flex justify-between items-center mb-8">
        <div>
            <h1 class="text-5xl font-black neon">CHARLYSCAN</h1>
            <p class="text-gray-400">Explorador Blockchain PRO</p>
        </div>

        <div class="card p-4">
            <p class="text-sm text-gray-400">Estado Nodo</p>
            <p class="text-green-400 font-bold blink">● EN VIVO</p>
            <p id="total-blocks" class="text-xl mt-2">Bloques: 0</p>
        </div>
    </div>

    <!-- SEARCH -->
    <div class="card p-6 mb-6">
        <p class="text-sm text-gray-400 mb-2">Wallet Tracker</p>

        <div class="flex gap-2">
            <input id="wallet-input"
                   class="w-full p-3 bg-black border border-gray-700 rounded text-cyan-300"
                   placeholder="Pega tu wallet..." />

            <button onclick="updateDashboard()"
                    class="bg-cyan-600 px-6 rounded font-bold">
                BUSCAR
            </button>
        </div>
    </div>

    <!-- STATS -->
    <div class="grid grid-cols-3 gap-4 mb-6">

        <div class="card p-5">
            <p class="text-gray-400">Saldo</p>
            <p id="user-balance" class="text-3xl text-yellow-400 font-bold">0 CHC</p>
        </div>

        <div class="card p-5">
            <p class="text-gray-400">Supply</p>
            <p id="total-supply" class="text-3xl font-bold">0 CHC</p>
        </div>

        <div class="card p-5">
            <p class="text-gray-400">Última Recompensa</p>
            <p id="last-reward" class="text-3xl text-purple-400 font-bold">0 CHC</p>
        </div>

    </div>

    <!-- TABLE -->
    <div class="card overflow-hidden">
        <div class="p-4 border-b border-gray-800">
            <h2 class="font-bold">Blockchain Explorer</h2>
        </div>

        <table class="w-full text-left">
            <thead class="text-gray-400 text-sm">
                <tr>
                    <th class="p-3">Bloque</th>
                    <th class="p-3">Wallet</th>
                    <th class="p-3">Monto</th>
                    <th class="p-3">Hash</th>
                </tr>
            </thead>

            <tbody id="blockchain-table"></tbody>
        </table>
    </div>

</div>

<!-- ================= JS PRO ================= -->
<script>
const API_CHAIN = window.location.origin + '/cadena';
const API_STATS = window.location.origin + '/stats';

async function updateDashboard() {
    try {
        const wallet = document.getElementById('wallet-input').value.trim();

        const [chainRes, statsRes] = await Promise.all([
            fetch(API_CHAIN),
            fetch(API_STATS)
        ]);

        const chain = await chainRes.json();
        const stats = await statsRes.json();

        let tableHtml = "";

        const recentBlocks = [...chain].reverse();

        recentBlocks.forEach(block => {
            const tx = block.transacciones?.[0];
            if (!tx) return;

            tableHtml += `
            <tr class="border-t border-gray-800 hover:bg-gray-900">
                <td class="p-3 text-cyan-400">#${block.indice}</td>
                <td class="p-3 text-xs">${tx.receptor}</td>
                <td class="p-3 text-yellow-400 font-bold">+${tx.monto}</td>
                <td class="p-3 text-[10px] text-gray-500">${block.hash.substring(0,32)}...</td>
            </tr>
            `;
        });

        document.getElementById("blockchain-table").innerHTML = tableHtml;

        document.getElementById("total-blocks").innerText =
            "Bloques: " + stats.bloques;

        document.getElementById("total-supply").innerText =
            Number(stats.recompensa).toLocaleString() + " CHC";

        document.getElementById("last-reward").innerText =
            stats.recompensa + " CHC";

        // 🔥 SALDO REAL
        if(wallet !== ""){
            const balRes = await fetch("/balance/" + wallet);
            const bal = await balRes.json();

            document.getElementById("user-balance").innerText =
                Number(bal.balance).toLocaleString() + " CHC";
        }

    } catch(e){
        console.log("Error dashboard:", e);
    }
}

setInterval(updateDashboard, 10000);
updateDashboard();
</script>

</body>
</html>
"""

# ==========================================
# HASH
# ==========================================
def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)

    texto = json.dumps(copia, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()

# ==========================================
# GENESIS
# ==========================================
def crear_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": 0,
            "hash_anterior": "0"
        }

        bloque["hash"] = calcular_hash(bloque)

        try:
            collection.insert_one(bloque)
        except:
            pass

# ==========================================
# RECOMPENSA
# ==========================================
def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    recompensa = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(recompensa, 0.00000001)

# ==========================================
# HOME
# ==========================================
@app.route("/")
def home():
    return render_template_string(HTML)

# ==========================================
# HEALTH
# ==========================================
@app.route("/health")
def health():
    return jsonify({"status": "online"})

# ==========================================
# STATS
# ==========================================
@app.route("/stats")
def stats():

    total = collection.count_documents({})

    # 🔥 CALCULAR SUPPLY REAL
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": {"$ne": None}}},
        {"$group": {
            "_id": None,
            "total_supply": {"$sum": "$transacciones.monto"}
        }}
    ]

    result = list(collection.aggregate(pipeline))

    supply = result[0]["total_supply"] if result else 0

    return jsonify({
        "bloques": max(total - 1, 0),
        "supply": round(supply, 2),
        "recompensa": recompensa_actual(),
        "dificultad": DIFICULTAD
    })

# ==========================================
# CADENA
# ==========================================
@app.route("/cadena")
def cadena():

    datos = list(
        collection.find({}, {"_id": 0})
        .sort("indice", DESCENDING)
        .limit(100)
    )

    datos.reverse()

    return jsonify(datos)

# ==========================================
# BALANCE
# ==========================================
@app.route("/balance/<wallet>")
def balance(wallet):

    total = 0.0

    bloques = collection.find(
        {"transacciones.receptor": wallet},
        {"_id": 0}
    )

    for bloque in bloques:
        for tx in bloque["transacciones"]:
            if tx["receptor"] == wallet:
                total += float(tx["monto"])

    return jsonify({
        "wallet": wallet,
        "balance": total
    })

# ==========================================
# MINAR
# ==========================================
@app.route("/minar", methods=["POST"])
def minar():

    data = request.get_json(force=True)

    wallet = str(data.get("wallet", "")).strip()
    nonce = str(data.get("nonce", "")).strip()

    if wallet == "":
        return jsonify({"error": "wallet requerida"}), 400

    ahora = time.time()

    # Anti spam
    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < 2:
            return jsonify({"error": "espera 2 segundos"}), 429

    # POW
    prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "hash invalido"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])

    if not ultimo:
        crear_genesis()
        ultimo = collection.find_one(sort=[("indice", -1)])

    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [
            {
                "emisor": "RED",
                "receptor": wallet,
                "monto": recompensa_actual()
            }
        ],
        "nonce": nonce,
        "hash_anterior": ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)

    try:
        collection.insert_one(nuevo)
    except DuplicateKeyError:
        return jsonify({"error": "bloque duplicado"}), 400
    except:
        return jsonify({"error": "error insertando bloque"}), 500

    ULTIMO_MINADO[wallet] = ahora

    return jsonify({
        "ok": True,
        "bloque": nuevo["indice"],
        "recompensa": nuevo["transacciones"][0]["monto"],
        "hash": nuevo["hash"]
    })

# ==========================================
# START
# ==========================================
crear_genesis()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
