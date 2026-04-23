import os
import time
import json
import hashlib
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient

# ==================================================
# 🚀 APP PRO CHC NODE
# ==================================================
app = Flask(__name__)
CORS(app)

# ==================================================
# 🔐 MONGODB
# En Render crear variable:
# MONGO_URI = mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&appName=Cluster0
# ==================================================
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&appName=Cluster0"
)

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = client["charlycoin_db"]
collection = db["blockchain"]

# probar conexión
client.server_info()

# ==================================================
# ⚙️ RED CHC
# ==================================================
DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000

# ==================================================
# 🎨 PANEL WEB
# ==================================================
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CHARLYSCAN PRO</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body{background:#050816;color:#fff}
</style>
</head>
<body class="p-6">
<div class="max-w-6xl mx-auto">

<h1 class="text-5xl font-black text-cyan-400 mb-8">
CHARLYSCAN PRO
</h1>

<div class="grid md:grid-cols-3 gap-4 mb-6">
<div class="bg-gray-900 p-5 rounded-xl">
<p class="text-gray-400">Bloques</p>
<p id="bloques" class="text-3xl font-bold">0</p>
</div>

<div class="bg-gray-900 p-5 rounded-xl">
<p class="text-gray-400">Supply</p>
<p id="supply" class="text-3xl font-bold text-yellow-400">0</p>
</div>

<div class="bg-gray-900 p-5 rounded-xl">
<p class="text-gray-400">Nodo</p>
<p class="text-green-400 font-bold">ONLINE</p>
</div>
</div>

<div class="mb-6">
<input id="wallet" placeholder="Wallet..."
class="w-full p-4 rounded text-black">
<button onclick="buscar()"
class="bg-cyan-500 px-5 py-3 rounded mt-2 font-bold">
BUSCAR BALANCE
</button>
<p id="balance" class="mt-3 text-xl text-yellow-400"></p>
</div>

<div class="bg-gray-900 rounded-xl overflow-hidden">
<table class="w-full text-sm">
<thead class="bg-gray-800">
<tr>
<th class="p-3">#</th>
<th class="p-3">Wallet</th>
<th class="p-3">Monto</th>
<th class="p-3">Hash</th>
</tr>
</thead>
<tbody id="tabla"></tbody>
</table>
</div>

</div>

<script>
async function cargar(){
try{
let r = await fetch('/cadena');
let data = await r.json();

let tabla = "";
let supply = 0;

[...data].reverse().forEach(b=>{
if(b.transacciones.length){
let tx = b.transacciones[0];
supply += parseFloat(tx.monto);

tabla += `
<tr class='border-b border-gray-800'>
<td class='p-2'>${b.indice}</td>
<td class='p-2'>${tx.receptor}</td>
<td class='p-2 text-yellow-400'>${tx.monto}</td>
<td class='p-2'>${b.hash.substring(0,18)}...</td>
</tr>
`;
}
});

document.getElementById("tabla").innerHTML = tabla;
document.getElementById("bloques").innerText = data.length - 1;
document.getElementById("supply").innerText = supply.toFixed(2)+" CHC";

}catch(e){
console.log(e);
}
}

async function buscar(){
let wallet = document.getElementById("wallet").value.trim();
if(!wallet)return;

let r = await fetch('/balance/'+wallet);
let d = await r.json();

document.getElementById("balance").innerText =
"Balance: "+d.balance+" CHC";
}

setInterval(cargar,10000);
cargar();
</script>

</body>
</html>
"""

# ==================================================
# 🔒 FUNCIONES
# ==================================================
def calcular_hash(bloque):
    limpio = {k: v for k, v in bloque.items() if k not in ["_id", "hash"]}
    texto = json.dumps(limpio, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()


def crear_genesis():
    if collection.count_documents({}) == 0:
        genesis = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": 0,
            "hash_anterior": "0"
        }
        genesis["hash"] = calcular_hash(genesis)
        collection.insert_one(genesis)


def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA
    recompensa = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(recompensa, 0.00000001)


# ==================================================
# 🌍 RUTAS
# ==================================================
@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/cadena")
def cadena():
    try:
        data = list(collection.find({}, {"_id": 0}))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/balance/<wallet>")
def balance(wallet):
    total = 0

    bloques = list(collection.find({}, {"_id": 0}))

    for b in bloques:
        for tx in b["transacciones"]:
            if tx["receptor"] == wallet:
                total += tx["monto"]

            if tx["emisor"] == wallet:
                total -= tx["monto"]

    return jsonify({
        "wallet": wallet,
        "balance": round(total, 8)
    })


@app.route("/minar", methods=["POST"])
def minar():
    try:
        data = request.json

        wallet = data.get("wallet")
        nonce = str(data.get("nonce"))

        if not wallet:
            return jsonify({"error": "wallet requerida"}), 400

        prueba = hashlib.sha256(
            f"{wallet}{nonce}".encode()
        ).hexdigest()

        if not prueba.startswith("0" * DIFICULTAD):
            return jsonify({"error": "hash invalido"}), 400

        ultimo = collection.find_one(sort=[("indice", -1)])

        nuevo = {
            "indice": ultimo["indice"] + 1,
            "timestamp": time.time(),
            "transacciones": [{
                "emisor": "RED",
                "receptor": wallet,
                "monto": recompensa_actual()
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================================================
# 🚀 INICIO
# ==================================================
crear_genesis()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
