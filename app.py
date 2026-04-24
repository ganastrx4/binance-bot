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
<title>CharlyScan - Panel En Vivo</title>

<script src="https://cdn.tailwindcss.com"></script>

<style>
body{
    background:#070b14;
    color:#f8fafc;
    font-family:'Segoe UI',Tahoma,Verdana,sans-serif;
}
.card{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:16px;
    box-shadow:0 10px 15px rgba(0,0,0,.45);
}
.neon-text{
    color:#00f2ff;
    text-shadow:0 0 14px rgba(0,242,255,.65);
}
.neon-border:focus{
    border-color:#00f2ff;
    box-shadow:0 0 12px rgba(0,242,255,.25);
}
.blink{
    animation:blink 1.5s infinite;
}
@keyframes blink{
    0%{opacity:1}
    50%{opacity:.35}
    100%{opacity:1}
}
::-webkit-scrollbar{
    width:8px;
}
::-webkit-scrollbar-thumb{
    background:#1f2937;
    border-radius:10px;
}
</style>
</head>

<body class="p-4 md:p-10">

<div class="max-w-7xl mx-auto">

<!-- HEADER -->
<header class="flex flex-col md:flex-row justify-between items-center gap-4 mb-10">

<div>
<h1 class="text-5xl font-black neon-text tracking-tighter">CHARLYSCAN</h1>
<p class="text-slate-500 text-sm font-mono">
Explorador de bloques para NewWorld Network
</p>
</div>

<div class="card p-4 flex items-center gap-4">

<div class="text-right">
<p class="text-xs uppercase tracking-widest text-slate-400">
Estado del Nodo
</p>

<p class="text-green-400 font-bold flex items-center justify-end gap-2">
<span class="blink">●</span> EN VIVO
</p>
</div>

<div class="h-10 w-px bg-slate-700"></div>

<div>
<p id="total-blocks"
class="text-2xl font-bold font-mono">
Bloques: 0
</p>
</div>

</div>

</header>

<!-- BUSCADOR -->
<div class="card p-6 mb-8 border-l-4 border-l-cyan-500">

<label class="block mb-3 text-sm font-semibold text-slate-300">
Rastreador de Minería Personal
</label>

<div class="flex gap-2">

<input
id="wallet-input"
type="text"
placeholder="Pega aquí tu dirección pública (Wallet) y pulsa Enter..."
class="w-full bg-black/50 border border-slate-700 p-4 rounded-xl focus:outline-none neon-border text-cyan-400 font-mono"
/>

<button
onclick="updateDashboard()"
class="bg-cyan-600 hover:bg-cyan-500 px-6 rounded-xl font-bold transition-all">
BUSCAR
</button>

</div>

</div>

<!-- STATS -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">

<div class="card p-8 border-l-4 border-l-yellow-500">
<h3 class="text-xs uppercase tracking-widest text-slate-400 mb-4">
Mi Saldo Acumulado
</h3>
<p id="user-balance"
class="text-4xl font-black text-yellow-400 font-mono">
0.00 CHC
</p>
</div>

<div class="card p-8">
<h3 class="text-xs uppercase tracking-widest text-slate-400 mb-4">
Suministro en Circulación
</h3>
<p id="total-supply"
class="text-4xl font-black font-mono">
0 CHC
</p>
</div>

<div class="card p-8">
<h3 class="text-xs uppercase tracking-widest text-slate-400 mb-4">
Última Recompensa
</h3>
<p id="reward"
class="text-4xl font-black text-green-400 font-mono">
0
</p>
</div>

<div class="card p-8">
<h3 class="text-xs uppercase tracking-widest text-slate-400 mb-4">
Dificultad de Red
</h3>
<p id="difficulty"
class="text-4xl font-black text-purple-500 font-mono">
5 ZEROS
</p>
</div>

</div>

<!-- TABLA -->
<div class="card overflow-hidden">

<div class="p-5 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">

<h2 class="font-bold text-lg">
Historial Reciente de la Blockchain
</h2>

<span class="text-xs text-slate-500">
NODO MAESTRO: RENDER CLOUD
</span>

</div>

<div class="overflow-x-auto">

<table class="w-full text-left">

<thead class="bg-slate-900 text-slate-500 text-xs uppercase">
<tr>
<th class="p-5">Bloque</th>
<th class="p-5">Wallet</th>
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

const API_CHAIN = "/cadena";
const API_STATS = "/stats";

async function updateDashboard(){

try{

const [chainRes, statsRes] = await Promise.all([
fetch(API_CHAIN),
fetch(API_STATS)
]);

const chain = await chainRes.json();
const stats = await statsRes.json();

const myWallet = document.getElementById("wallet-input").value.trim();

let userBalance = 0;
let totalSupply = 0;
let html = "";

const recent = [...chain].reverse();

recent.forEach(block=>{

if(!block.transacciones || !block.transacciones.length) return;

const tx = block.transacciones[0];
const monto = parseFloat(tx.monto || 0);

totalSupply += monto;

if(myWallet !== "" && tx.receptor === myWallet){
userBalance += monto;
}

html += `
<tr class="hover:bg-slate-800/40 transition-all">
<td class="p-5 text-cyan-400 font-bold">#${block.indice}</td>

<td class="p-5 text-xs text-slate-400 font-mono">
${tx.receptor}
</td>

<td class="p-5 text-yellow-400 font-black">
+${monto.toLocaleString()}
</td>

<td class="p-5 text-[10px] text-slate-600 font-mono">
${block.hash.substring(0,32)}...
</td>
</tr>
`;

});

document.getElementById("blockchain-table").innerHTML =
html || `<tr><td colspan="4" class="p-10 text-center text-slate-500">Sin bloques</td></tr>`;

document.getElementById("user-balance").innerText =
userBalance.toLocaleString(undefined,{minimumFractionDigits:2}) + " CHC";

document.getElementById("total-supply").innerText =
totalSupply.toLocaleString() + " CHC";

document.getElementById("total-blocks").innerText =
"Bloques: " + stats.bloques;

document.getElementById("reward").innerText =
stats.recompensa + " CHC";

document.getElementById("difficulty").innerText =
stats.dificultad + " ZEROS";

}catch(e){

document.getElementById("total-blocks").innerText = "Nodo Offline";

}

}

document.getElementById("wallet-input").addEventListener("keypress",function(e){
if(e.key==="Enter") updateDashboard();
});

setInterval(updateDashboard,10000);
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

    return jsonify({
        "bloques": max(total - 1, 0),
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
