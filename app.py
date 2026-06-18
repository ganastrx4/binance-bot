import os
import json
import time
import hashlib
import threading

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from web3 import Web3

# =====================================================
# APP
# =====================================================
app = Flask(__name__)
CORS(app)

# =====================================================
# CONFIG
# =====================================================
PORT = int(os.environ.get("PORT", 10000))

MONGO_URI = os.environ.get("MONGO_URI", "").strip()
if MONGO_URI == "":
    MONGO_URI = "mongodb+srv://charly:caseta82%2A@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority&tls=true"

DIFICULTAD = 5
RECOMPENSA_INICIAL = 18.0
HALVING_CADA = 21000
MAX_SUPPLY = 21000000000
COOLDOWN_MINADO = 2

ULTIMO_MINADO = {}

# =====================================================
# DB
# =====================================================
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=30000)
db = client["charlycoin_db"]
collection = db["blockchain"]

collection.create_index("hash")
try:
    collection.create_index([("indice", ASCENDING)], unique=True)
except:
    pass

# =====================================================
# HTML VISUAL INTERFACE (CHARLYSCAN)
# =====================================================
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CHARLYSCAN PRO</title>
<script src="https://cdn.tailwindcss.com"></script>

<style>
body{
    background:#070b14;
    color:#f8fafc;
    font-family:Segoe UI, Arial;
}
.card{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:16px;
}
.neon{
    color:#00f2ff;
    text-shadow:0 0 14px rgba(0,242,255,.55);
}
.blink{
    animation:blink 1.5s infinite;
}
@keyframes blink{
    0%{opacity:1}
    50%{opacity:.3}
    100%{opacity:1}
}
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
    <p class="text-sm text-gray-400 mb-2 font-bold uppercase tracking-widest">
        Wallet Tracker
    </p>

    <div class="flex gap-2">
        <input
            id="wallet-input"
            class="w-full p-3 bg-black border border-gray-700 rounded text-cyan-300 font-mono"
            placeholder="Ingresa tu dirección pública..."
        />
        <button onclick="updateDashboard()"
            class="bg-cyan-600 hover:bg-cyan-500 px-8 rounded font-bold">
            BUSCAR
        </button>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">

    <div class="card p-5 border-l-4 border-yellow-500">
        <p class="text-gray-400 text-xs font-bold uppercase">Mi Saldo</p>
        <p id="user-balance"
           class="text-3xl text-yellow-400 font-black font-mono">
           0.00 CHC
        </p>
    </div>

    <div class="card p-5 border-l-4 border-white">
        <p class="text-gray-400 text-xs font-bold uppercase">Suministro Actual</p>
        <p id="total-supply"
           class="text-3xl font-black font-mono text-white">
           0 CHC
        </p>
        <p class="text-gray-500 text-[10px] mt-1">
             MÁXIMO: 21,000,000,000 CHC
        </p>
    </div>

    <div class="card p-5 border-l-4 border-purple-500">
        <p class="text-gray-400 text-xs font-bold uppercase">Recompensa x Bloque</p>
        <p id="last-reward"
           class="text-3xl text-purple-400 font-black font-mono">
           0 CHC
        </p>
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
                    <th class="p-3">De</th>
                    <th class="p-3">A</th>
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
async function updateDashboard(){
    try{
        const wallet = document.getElementById("wallet-input").value.trim();

        const [chainRes, statsRes] = await Promise.all([
            fetch("/cadena"),
            fetch("/stats")
        ]);

        const chain = await chainRes.json();
        const stats = await statsRes.json();

        let html = "";

        chain.forEach(block => {
            const tx = block.transacciones?.[0];
            if(!tx) return;

            html += `
            <tr class="border-t border-gray-800 hover:bg-gray-900/40">
                <td class="p-3 text-cyan-400 font-bold">#${block.indice}</td>
                <td class="p-3 text-xs font-mono text-gray-400">
                    \${(tx.emisor || "").substring(0,18)}...
                </td>
                <td class="p-3 text-xs font-mono text-gray-400">
                    \${(tx.receptor || "").substring(0,18)}...
                </td>
                <td class="p-3 text-yellow-400 font-bold">
                    \${Number(tx.monto).toLocaleString()}
                </td>
                <td class="p-3 text-[10px] text-gray-600 font-mono">
                    \${block.hash.substring(0,24)}...
                </td>
            </tr>`;
        });

        document.getElementById("blockchain-table").innerHTML = html;
        document.getElementById("total-blocks").innerText = "Bloques: " + stats.bloques;
        document.getElementById("total-supply").innerText = stats.supply.toLocaleString() + " CHC";
        document.getElementById("last-reward").innerText = stats.recompensa + " CHC";

        if(wallet !== ""){
            const r = await fetch("/balance/" + wallet);
            const b = await r.json();

            document.getElementById("user-balance").innerText =
                Number(b.balance).toLocaleString(
                    undefined,
                    {minimumFractionDigits:2}
                ) + " CHC";
        }

    }catch(e){
        console.log(e);
    }
}

setInterval(updateDashboard, 10000);
updateDashboard();
</script>

</body>
</html>
"""

# =====================================================
# HELPERS
# =====================================================
def calcular_hash(bloque):
    copia = dict(bloque)
    copia.pop("_id", None)
    copia.pop("hash", None)

    texto = json.dumps(copia, sort_keys=True).encode()
    return hashlib.sha256(texto).hexdigest()


def crear_genesis():
    if collection.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "nonce": "0",
            "hash_anterior": "0"
        }

        bloque["hash"] = calcular_hash(bloque)
        collection.insert_one(bloque)


def recompensa_actual():
    bloques = collection.count_documents({})
    halvings = bloques // HALVING_CADA

    return max(
        RECOMPENSA_INICIAL / (2 ** halvings),
        0.00000001
    )


def saldo_wallet(wallet):
    pipeline = [
        {"$unwind": "$transacciones"},
        {
            "$match": {
                "$or": [
                    {"transacciones.receptor": wallet},
                    {"transacciones.emisor": wallet}
                ]
            }
        }
    ]

    movimientos = list(collection.aggregate(pipeline))
    saldo = 0.0

    for item in movimientos:
        tx = item["transacciones"]
        if tx.get("receptor") == wallet:
            saldo += float(tx.get("monto", 0))
        if tx.get("emisor") == wallet:
            saldo -= float(tx.get("monto", 0))

    return round(saldo, 8)


# =====================================================
# ⚡ FUNCIÓN INTERNA: ASIGNACIÓN AUTOMÁTICA DE CHC
# =====================================================
def forjar_bloque_compra(billetera_destino, monto_usdt):
    """Genera un bloque de asignación por compra directa indexado en MongoDB"""
    try:
        ultimo = collection.find_one(sort=[("indice", -1)])
        tasa_cambio = 0.85
        tokens_chc = round(monto_usdt / tasa_cambio, 6)

        nuevo_bloque = {
            "indice": ultimo["indice"] + 1,
            "timestamp": time.time(),
            "transacciones": [{
                "emisor": "TEMPO_POOL",
                "receptor": billetera_destino,
                "monto": tokens_chc,
                "firma": "LIQUIDITY_INJECTION"
            }],
            "nonce": "fiat_ramp",
            "hash_anterior": ultimo["hash"]
        }
        nuevo_bloque["hash"] = calcular_hash(nuevo_bloque)
        collection.insert_one(nuevo_bloque)
        print(f"[💎] Éxito: Bloque #{nuevo_bloque['indice']} forjado. {tokens_chc} CHC enviados a {billetera_destino}", flush=True)
    except Exception as e:
        print(f"[❌] Error al inyectar bloque de compra: {e}", flush=True)


# =====================================================
# 📡 DAEMON EN SEGUNDO PLANO: ESCUCHA DE PASARELA (USDT)
# =====================================================
def monitor_blockchain_tempo():
    print("[📡] Monitor Tempo iniciado. Escuchando la pool en Binance Smart Chain...", flush=True)
    
    w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))
    POOL_WALLET = "0x9D437783e3b940AC85557765D8b07fF7a69fB4e6"
    USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
    
    USDT_ABI = '[{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]'
    contrato_usdt = w3.eth.contract(address=w3.to_checksum_address(USDT_CONTRACT), abi=USDT_ABI)
    
    try:
        ultimo_bloque = w3.eth.block_number
    except:
        ultimo_bloque = 0

    while True:
        try:
            bloque_actual = w3.eth.block_number
            if bloque_actual > ultimo_bloque:
                filtros = contrato_usdt.events.Transfer.create_filter(fromBlock=ultimo_bloque, toBlock=bloque_actual)
                eventos = filtros.get_all_entries()
                
                for evento in eventos:
                    if evento.args.to.lower() == POOL_WALLET.lower():
                        monto_usdt = evento.args.value / (10**18)
                        tx_hash = evento.transactionHash.hex()
                        
                        tx_data = w3.eth.get_transaction(tx_hash)
                        input_hex = tx_data.get('input', '')
                        
                        try:
                            memo_chc = bytes.fromhex(input_hex[10:]).decode('utf-8', errors='ignore').strip()
                            if len(memo_chc) > 20:
                                print(f"\n[💰] ¡Depósito detectado! {monto_usdt} USDT", flush=True)
                                forjar_bloque_compra(memo_chc, monto_usdt)
                        except:
                            print("[!] Transferencia recibida pero el campo MEMO no contiene datos legibles.", flush=True)
                            
                ultimo_bloque = bloque_actual
            time.sleep(4)
        except Exception as e:
            time.sleep(6)


# =====================================================
# ROUTES
# =====================================================
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/stats")
def stats():
    total = collection.count_documents({})
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]
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
    data = list(collection.find({}, {"_id": 0}).sort("indice", DESCENDING).limit(50))
    return jsonify(data)

@app.route("/balance/<wallet>")
def balance(wallet):
    return jsonify({"wallet": wallet, "balance": saldo_wallet(wallet)})

@app.route("/transferir", methods=["POST"])
def transferir():
    data = request.get_json(force=True)
    emisor = str(data.get("emisor", "")).strip()
    receptor = str(data.get("receptor", "")).strip()
    try:
        monto = float(data.get("monto", 0))
    except:
        return jsonify({"mensaje": "monto inválido"}), 400

    firma = str(data.get("firma", "")).strip()
    if not emisor or not receptor or monto <= 0:
        return jsonify({"mensaje": "datos incompletos"}), 400
    if emisor == receptor:
        return jsonify({"mensaje": "no puedes enviarte a ti mismo"}), 400

    if saldo_wallet(emisor) < monto:
        return jsonify({"mensaje": "saldo insuficiente"}), 400

    ultimo = collection.find_one(sort=[("indice", -1)])
    nuevo = {
        "indice": ultimo["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{"emisor": emisor, "receptor": receptor, "monto": monto, "firma": firma}],
        "nonce": "transfer",
        "hash_anterior": ultimo["hash"]
    }
    nuevo["hash"] = calcular_hash(nuevo)
    try:
        collection.insert_one(nuevo)
        return jsonify({"ok": True, "mensaje": "transferencia enviada"})
    except:
        return jsonify({"mensaje": "error de red"}), 500

@app.route("/minar", methods=["POST"])
def minar():
    data = request.get_json(force=True)
    wallet = str(data.get("wallet", "")).strip()
    nonce = str(data.get("nonce", "")).strip()

    if not wallet or not nonce:
        return jsonify({"error": "datos incompletos"}), 400

    ahora = time.time()
    if wallet in ULTIMO_MINADO:
        if ahora - ULTIMO_MINADO[wallet] < COOLDOWN_MINADO:
            return jsonify({"error": "espera 2 seg"}), 429

    prueba = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()
    if not prueba.startswith("0" * DIFICULTAD):
        return jsonify({"error": "hash invalido"}), 400

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

# =====================================================
# START
# =====================================================
if __name__ == "__main__":
    crear_genesis()
    
    hilo_pool = threading.Thread(target=monitor_blockchain_tempo, daemon=True)
    hilo_pool.start()
    
    app.run(host="0.0.0.0", port=PORT)
