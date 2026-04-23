import hashlib
import json
import time
import os
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚙️ CONFIGURACIÓN PRO MONGODB
# ==========================================
# En Render pon esto en Environment Variables:
# Key: MONGO_URI
# Value:
# mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&appName=Cluster0

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&appName=Cluster0"
)

client = MongoClient(MONGO_URI)
db = client["charlycoin_db"]
collection = db["blockchain"]

# ==========================================
# ⚙️ RED
# ==========================================
DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000

# ==========================================
# 🎨 HTML
# ==========================================
HTML_INDEX = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CHARLYSCAN PRO</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body{background:#070b14;color:#fff}
</style>
</head>
<body class="p-8">
<div class="max-w-6xl mx-auto">
<h1 class="text-5xl font-black text-cyan-400 mb-6">CHARLYSCAN PRO</h1>

<div class="mb-6">
<input id="wallet-input" class="border p-3 text-black w-full"
placeholder="Wallet para revisar balance">
<button onclick="updateDashboard()" class="bg-cyan-500 px-5 py-3 mt-2 rounded">
BUSCAR
</button>
</div>

<div class="grid md:grid-cols-3 gap-4 mb-6">
<div class="bg-gray-900 p-4 rounded">
<p>Bloques</p>
<p id="total-blocks">0</p>
</div>

<div class="bg-gray-900 p-4 rounded">
<p>Supply</p>
<p id="total-supply">0 CHC</p>
</div>

<div class="bg-gray-900 p-4 rounded">
<p>Mi Balance</p>
<p id="user-balance">0 CHC</p>
</div>
</div>

<table class="w-full text-sm bg-gray-900 rounded overflow-hidden">
<thead class="bg-gray-800">
<tr>
<th class="p-2">Bloque</th>
<th class="p-2">Wallet</th>
<th class="p-2">Monto</th>
<th class="p-2">Hash</th>
</tr>
</thead>
<tbody id="blockchain-table"></tbody>
</table>
</div>

<script>
const API_URL = window.location.origin + "/cadena";

async function updateDashboard(){
try{
const r = await fetch(API_URL);
const chain = await r.json();

let totalSupply = 0;
let userBalance = 0;
let html = "";
let wallet = document.getElementById("wallet-input").value.trim();

[...chain].reverse().forEach(block=>{
if(block.transacciones.length){
let tx = block.transacciones[0];
let monto = parseFloat(tx.monto);

totalSupply += monto;

if(wallet && tx.receptor === wallet){
userBalance += monto;
}

html += `
<tr class="border-b border-gray-800">
<td class="p-2">#${block.indice}</td>
<td class="p-2">${tx.receptor}</td>
<td class="p-2 text-yellow-400">${monto}</td>
<td class="p-2">${block.hash.substring(0,18)}...</td>
</tr>
`;
}
});

document.getElementById("blockchain-table").innerHTML = html;
document.getElementById("total-blocks").innerText = chain.length - 1;
document.getElementById("total-supply").innerText = totalSupply + " CHC";
document.getElementById("user-balance").innerText = userBalance + " CHC";

}catch(e){
console.log(e);
}
}

setInterval(updateDashboard,10000);
updateDashboard();
</script>
</body>
</html>
"""

# ==========================================
# 🔒 FUNCIONES
# ==========================================
def calcular_hash(bloque):
    limpio = {k: v for k, v in bloque.items() if k not in ["_id", "hash"]}
    texto = json.dumps(limpio, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()

def crear_bloque_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": 0,
            "hash_anterior": "0"
        }
        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)

def calcular_recompensa():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    recompensa = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(recompensa, 0.00000001)

# ==========================================
# 🌍 RUTAS
# ==========================================
@app.route("/")
def home():
    return render_template_string(HTML_INDEX)

@app.route("/cadena", methods=["GET"])
def cadena():
    return jsonify(list(collection.find({}, {"_id": 0})))

@app.route("/balance/<wallet>", methods=["GET"])
def balance(wallet):
    total = 0
    bloques = list(collection.find({}, {"_id": 0}))

    for bloque in bloques:
        for tx in bloque["transacciones"]:
            if tx["receptor"] == wallet:
                total += tx["monto"]
            if tx["emisor"] == wallet:
                total -= tx["monto"]

    return jsonify({
        "wallet": wallet,
        "balance": total
    })

@app.route("/minar", methods=["POST"])
def minar():
    data = request.json

    wallet = data.get("wallet")
    nonce = data.get("nonce")

    if not wallet:
        return jsonify({"error": "wallet requerida"}), 400

    hash_prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not hash_prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "hash inválido"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])

    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{
            "emisor": "RED",
            "receptor": wallet,
            "monto": calcular_recompensa()
        }],
        "nonce": nonce,
        "hash_anterior": ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)
    collection.insert_one(nuevo)

    return jsonify({
        "ok": True,
        "bloque": nuevo
    })

# ==========================================
# 🚀 INICIO
# ==========================================
if __name__ == "__main__":
    crear_bloque_genesis()
    app.run(host="0.0.0.0", port=10000)
