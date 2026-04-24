# ==========================================
# 🚀 CHARLYCOIN NODE FULL PRO + PANEL BONITO
# Render + MongoDB + API + Dashboard HTML
# Archivo: app.py
# ==========================================

import os
import json
import time
import hashlib

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
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

if not MONGO_URI:
    raise Exception("Falta MONGO_URI en Render")

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
    socketTimeoutMS=30000
)

db = client["charlycoin_db"]
collection = db["blockchain"]

# Solo índice hash
collection.create_index("hash")

# ==========================================
# HASH
# ==========================================
def calcular_hash(b):
    data = dict(b)
    data.pop("_id", None)
    data.pop("hash", None)

    texto = json.dumps(data, sort_keys=True).encode()
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
    r = RECOMPENSA_INICIAL / (2 ** halvings)
    return max(r, 0.00000001)

# ==========================================
# HOME HTML PRO
# ==========================================
HTML = """
<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>CHARLYSCAN</title>
<script src='https://cdn.tailwindcss.com'></script>

<style>
body{
background:#070b14;
color:white;
font-family:Arial;
}
.card{
background:#111827;
border-radius:18px;
padding:20px;
box-shadow:0 0 15px rgba(0,0,0,.4);
}
.neon{
color:#00f2ff;
text-shadow:0 0 10px #00f2ff;
}
</style>
</head>

<body class='p-6'>

<div class='max-w-6xl mx-auto'>

<div class='flex justify-between items-center mb-8'>
<div>
<h1 class='text-5xl font-black neon'>CHARLYSCAN</h1>
<p class='text-gray-400'>Explorador de bloques para NewWorld Network</p>
</div>

<div class='card text-right'>
<p class='text-sm text-gray-400'>Estado del Nodo</p>
<p class='text-green-400 font-bold'>● EN VIVO</p>
<p id='bloques' class='text-2xl font-bold'>Bloques: ...</p>
</div>
</div>

<div class='card mb-6'>
<p class='mb-2 text-sm text-gray-400'>Rastreador de Minería Personal</p>
<div class='flex gap-2'>
<input id='wallet' placeholder='Pega aquí tu wallet'
class='w-full bg-black p-3 rounded text-cyan-400'>
<button onclick='buscarWallet()'
class='bg-cyan-600 px-5 rounded font-bold'>BUSCAR</button>
</div>
</div>

<div class='grid md:grid-cols-3 gap-4 mb-8'>

<div class='card'>
<p class='text-gray-400'>Mi Saldo Acumulado</p>
<p id='saldo' class='text-3xl text-yellow-400 font-bold'>0 CHC</p>
</div>

<div class='card'>
<p class='text-gray-400'>Suministro en Circulación</p>
<p id='supply' class='text-3xl font-bold'>...</p>
</div>

<div class='card'>
<p class='text-gray-400'>Dificultad de Red</p>
<p class='text-3xl text-purple-400 font-bold'>5 ZEROS</p>
</div>

</div>

<div class='card'>
<h2 class='text-xl font-bold mb-4'>Últimos Bloques</h2>

<div class='overflow-auto'>
<table class='w-full text-left'>
<thead>
<tr class='text-gray-400'>
<th>#</th>
<th>Wallet</th>
<th>Monto</th>
<th>Hash</th>
</tr>
</thead>
<tbody id='tabla'></tbody>
</table>
</div>

</div>

</div>

<script>

async function cargar(){

let r = await fetch('/cadena');
let data = await r.json();

document.getElementById("bloques").innerText =
"Bloques: " + (data.length ? data[data.length-1].indice : 0);

let html = "";
let supply = 0;

data.reverse().slice(0,100).forEach(b=>{

if(b.transacciones.length){

let tx = b.transacciones[0];
supply += parseFloat(tx.monto);

html += `
<tr class='border-b border-gray-800'>
<td class='py-2'>#${b.indice}</td>
<td class='text-xs'>${tx.receptor}</td>
<td class='text-yellow-400'>+${tx.monto}</td>
<td class='text-xs text-gray-500'>${b.hash.substring(0,30)}...</td>
</tr>
`;

}

});

document.getElementById("tabla").innerHTML = html;
document.getElementById("supply").innerText =
supply.toLocaleString() + " CHC";

}

async function buscarWallet(){

let wallet = document.getElementById("wallet").value.trim();

if(!wallet)return;

let r = await fetch('/balance/'+wallet);
let d = await r.json();

document.getElementById("saldo").innerText =
d.balance.toLocaleString() + " CHC";

}

setInterval(cargar,5000);
cargar();

</script>

</body>
</html>
"""

# ==========================================
# ROUTES
# ==========================================
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/health")
def health():
    return jsonify({"status":"online"})

@app.route("/stats")
def stats():
    total = collection.count_documents({})
    return jsonify({
        "bloques": max(total-1,0),
        "dificultad": DIFICULTAD,
        "recompensa": recompensa_actual()
    })

@app.route("/cadena")
def cadena():
    datos = list(
        collection.find({}, {"_id":0})
        .sort("indice", DESCENDING)
        .limit(100)
    )

    datos.reverse()
    return jsonify(datos)

@app.route("/balance/<wallet>")
def balance(wallet):

    total = 0

    bloques = collection.find(
        {"transacciones.receptor": wallet},
        {"_id":0}
    )

    for b in bloques:
        for tx in b["transacciones"]:
            if tx["receptor"] == wallet:
                total += float(tx["monto"])

    return jsonify({
        "wallet": wallet,
        "balance": total
    })

@app.route("/minar", methods=["POST"])
def minar():

    data = request.get_json(force=True)

    wallet = str(data.get("wallet","")).strip()
    nonce = str(data.get("nonce","")).strip()

    if not wallet:
        return jsonify({"error":"wallet requerida"}),400

    ahora = time.time()

    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < 2:
            return jsonify({"error":"espera 2 segundos"}),429

    prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not prueba.startswith("0"*DIFICULTAD):
        return jsonify({"error":"hash invalido"}),400

    ultimo = collection.find_one(sort=[("indice",-1)])

    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": time.time(),
        "transacciones":[
            {
                "emisor":"RED",
                "receptor":wallet,
                "monto":recompensa_actual()
            }
        ],
        "nonce":nonce,
        "hash_anterior":ultimo["hash"]
    }

    nuevo["hash"] = calcular_hash(nuevo)

    try:
        collection.insert_one(nuevo)
    except DuplicateKeyError:
        return jsonify({"error":"duplicado"}),400

    ULTIMO_MINADO[wallet] = ahora

    return jsonify({
        "ok":True,
        "bloque":nuevo["indice"],
        "hash":nuevo["hash"]
    })

# ==========================================
# START
# ==========================================
crear_genesis()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
