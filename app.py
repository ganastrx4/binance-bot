import os
import time
import hashlib
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
PORT = int(os.environ.get("PORT", 10000))
MONGO_URI = os.environ.get("MONGO_URI", "")

if not MONGO_URI:
    MONGO_URI = "mongodb+srv://charly:caseta82*@cluster0.daebfm2.mongodb.net/charlycoin_db?retryWrites=true&w=majority"

DIFICULTAD = 5
RECOMPENSA = 18.0
CHOROX_RATE = 1  # 1 CHC = 1 CHOROX (ajústalo)

client = MongoClient(MONGO_URI)
db = client["charlycoin_db"]

chain = db["blockchain"]
wallets = db["wallets"]
txs = db["transacciones"]

try:
    chain.create_index([("indice", ASCENDING)], unique=True)
except Exception as e:
    print("Index ya existe:", e)

# =========================
# GENESIS
# =========================
def genesis():
    if chain.count_documents({}) == 0:
        bloque = {
            "indice": 0,
            "timestamp": time.time(),
            "transacciones": [],
            "hash_anterior": "0",
            "nonce": "0"
        }
        bloque["hash"] = hashlib.sha256(json.dumps(bloque).encode()).hexdigest()
        chain.insert_one(bloque)

# =========================
# HASH
# =========================
def hash_block(b):
    b = dict(b)
    b.pop("_id", None)
    b.pop("hash", None)
    return hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()

# =========================
# BALANCE
# =========================
@app.route("/balance/<wallet>")
def balance(wallet):
    pipeline = [
        {"$unwind": "$transacciones"},
        {"$match": {"transacciones.receptor": wallet}},
        {"$group": {"_id": None, "total": {"$sum": "$transacciones.monto"}}}
    ]
    res = list(chain.aggregate(pipeline))
    return jsonify({"balance": res[0]["total"] if res else 0})

# =========================
# MINAR
# =========================
@app.route("/minar", methods=["POST"])
def minar():
    data = request.get_json()
    wallet = data.get("wallet")
    nonce = data.get("nonce")

    if not wallet:
        return jsonify({"error": "wallet faltante"}), 400

    h = hashlib.sha256(f"{wallet}{nonce}".encode()).hexdigest()

    if not h.startswith("0" * DIFICULTAD):
        return jsonify({"error": "invalid hash"}), 400

    last = chain.find_one(sort=[("indice", -1)])

    bloque = {
        "indice": last["indice"] + 1,
        "timestamp": time.time(),
        "transacciones": [{
            "emisor": "RED",
            "receptor": wallet,
            "monto": RECOMPENSA
        }],
        "nonce": nonce,
        "hash_anterior": last["hash"]
    }

    bloque["hash"] = hash_block(bloque)
    chain.insert_one(bloque)

    # crear wallet si no existe
    if not wallets.find_one({"wallet": wallet}):
        wallets.insert_one({"wallet": wallet, "chc": 0, "chorox": 0})

    wallets.update_one(
        {"wallet": wallet},
        {"$inc": {"chc": RECOMPENSA}},
        upsert=True
    )

    return jsonify({"ok": True})

# =========================
# TRANSFERIR CHC
# =========================
@app.route("/transferir", methods=["POST"])
def transferir():
    d = request.get_json()

    emisor = d["emisor"]
    receptor = d["receptor"]
    monto = float(d["monto"])

    w1 = wallets.find_one({"wallet": emisor})
    if not w1:
        return jsonify({"error": "wallet emisor no existe"}), 404

    if w1["chc"] < monto:
        return jsonify({"error": "saldo insuficiente"}), 400

    wallets.update_one({"wallet": emisor}, {"$inc": {"chc": -monto}}, upsert=True)
    wallets.update_one({"wallet": receptor}, {"$inc": {"chc": monto}}, upsert=True)

    return jsonify({"ok": True})

# =========================
# SWAP CHC → CHOROX (MINT + BURN)
# =========================
@app.route("/swap", methods=["POST"])
def swap():
    data = request.get_json()
    wallet = data.get("wallet")
    amount = float(data.get("amount"))

    w = wallets.find_one({"wallet": wallet})
    if not w or w["chc"] < amount:
        return jsonify({"error": "sin fondos"}), 400

    # burn CHC
    wallets.update_one({"wallet": wallet}, {"$inc": {"chc": -amount}})

    # mint CHOROX
    chorox = amount * CHOROX_RATE
    wallets.update_one({"wallet": wallet}, {"$inc": {"chorox": chorox}})

    return jsonify({
        "ok": True,
        "burned_chc": amount,
        "minted_chorox": chorox
    })

# =========================
# STATS
# =========================
@app.route("/stats")
def stats():
    return jsonify({
        "bloques": chain.count_documents({}),
        "supply": chain.count_documents({}) * RECOMPENSA
    })

# =========================
# BLOCKCHAIN
# =========================
@app.route("/cadena")
def cadena():
    return jsonify(list(chain.find({}, {"_id": 0}).sort("indice", DESCENDING).limit(50)))

# =========================
# home
# =========================

@app.route("/")
def home():

    html = """
<!DOCTYPE html>
<html>
<head>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>CHC CHARLYCOIN Super App</title>

<style>
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial,Helvetica,sans-serif;
    background:#050816;
    color:white;
    min-height:100vh;
}

.hero{
    padding:55px 25px 45px 25px;
    background:
    radial-gradient(circle at top right,#1d4ed8 0%,transparent 35%),
    radial-gradient(circle at top left,#06b6d4 0%,transparent 35%),
    linear-gradient(135deg,#0f172a,#111827,#0b1020);
    border-radius:0 0 35px 35px;
    box-shadow:0 10px 30px rgba(0,0,0,.45);
}

.badge{
    display:inline-block;
    padding:8px 14px;
    border-radius:30px;
    background:rgba(255,255,255,.08);
    font-size:12px;
    letter-spacing:1px;
    margin-bottom:18px;
    border:1px solid rgba(255,255,255,.08);
}

h1{
    font-size:34px;
    font-weight:900;
    margin-bottom:10px;
}

.sub{
    color:#cbd5e1;
    font-size:15px;
    line-height:1.6;
    max-width:560px;
}

.wrap{
    max-width:1180px;
    margin:auto;
    padding:24px;
}

.grid{
    display:grid;
    grid-template-columns: 1.2fr .8fr;
    gap:24px;
}

.card{
    background:#0f172a;
    border:1px solid #1e293b;
    border-radius:22px;
    padding:18px;
    box-shadow:0 8px 24px rgba(0,0,0,.25);
}

.btn{
    display:block;
    text-decoration:none;
    color:white;
    font-weight:700;
    padding:18px;
    border-radius:18px;
    margin-bottom:14px;
}

.wallet{background:linear-gradient(135deg,#2563eb,#1d4ed8);}
.scan{background:linear-gradient(135deg,#10b981,#059669);}
.stats{background:linear-gradient(135deg,#7c3aed,#6d28d9);}
.mine{background:linear-gradient(135deg,#f59e0b,#d97706);}
.trade{background:linear-gradient(135deg,#ec4899,#db2777);}
.swap{background:linear-gradient(135deg,#06b6d4,#0891b2);}
.market{background:linear-gradient(135deg,#ef4444,#dc2626);}

.side{
    background:#0f172a;
    border:1px solid #1e293b;
    border-radius:22px;
    padding:20px;
    box-shadow:0 8px 24px rgba(0,0,0,.25);
    height:fit-content;
}

.side h2{
    font-size:24px;
    margin-bottom:12px;
}

.reward{
    font-size:48px;
    font-weight:900;
    color:#22c55e;
    margin:12px 0;
}

.input{
    width:100%;
    padding:14px;
    border-radius:14px;
    border:none;
    outline:none;
    background:#111827;
    color:white;
    margin-top:10px;
}

.claim{
    width:100%;
    border:none;
    padding:16px;
    border-radius:16px;
    margin-top:14px;
    font-size:18px;
    font-weight:900;
    color:white;
    cursor:pointer;
    background:linear-gradient(135deg,#22c55e,#16a34a);
}

.claim:disabled{
    opacity:.5;
    cursor:not-allowed;
}

.small{
    color:#94a3b8;
    font-size:13px;
    margin-top:10px;
    line-height:1.5;
}

.timer{
    margin-top:14px;
    font-size:18px;
    font-weight:700;
    color:#f59e0b;
}

.status{
    margin-top:12px;
    font-size:14px;
    color:#22c55e;
}

.row{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:14px;
    margin-top:18px;
}

.mini{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:18px;
    padding:16px;
}

.mini small{
    color:#94a3b8;
    display:block;
    margin-bottom:8px;
}

.footer{
    text-align:center;
    color:#64748b;
    font-size:12px;
    padding:25px 0 10px;
}

@media(max-width:900px){
    .grid{
        grid-template-columns:1fr;
    }
}
</style>
</head>

<body>

<div class='hero'>
    <div class='badge'>CHC • WEB3 • BONUS DIARIO</div>
    <h1>💎 CHC SUPER APP - CHARLYCOIN</h1>
    <div class='sub'>
        Wallet descentralizada, explorer en vivo, minería CHC,
        swap y ahora recompensas diarias en CHOROX.
    </div>
</div>

<div class='wrap'>

<div class='grid'>

<div class='card'>
    <a class='btn wallet' href='/wallet'>💼 Abrir Wallet</a>
    <a class='btn scan' href='/scan'>⛓ Blockchain Explorer</a>
    <a class='btn stats' href='/stats'>📊 Estadísticas</a>
    <a class='btn mine' href='/cadena'>🚀 Últimos Bloques</a>
    <a class='btn trade' href='/trade'>📈 Comprar Criptos</a>
    <a class='btn swap' href='/swap'>🔄 Swap CHC ↔ CHOROX</a>
    <a class='btn market' href='/prices'>🔥 Mercado Binance</a>

    <div class='row'>
        <div class='mini'>
            <small>Token</small>
            <b>CHOROX</b>
        </div>

        <div class='mini'>
            <small>Red</small>
            <b>BSC</b>
        </div>

        <div class='mini'>
            <small>Minería</small>
            <b>CHC Network</b>
        </div>

        <div class='mini'>
            <small>Estado</small>
            <b style='color:#22c55e;'>● Online</b>
        </div>
    </div>
</div>

<div class='side'>

    <h2>🎁 Bonus Diario</h2>

    <div class='small'>
        Si minaste CHC en las últimas 24 horas puedes reclamar:
    </div>

    <div class='reward'>100 CHOROX</div>

    <input id='wallet' class='input'
    placeholder='Pega tu wallet BSC / minera'>

    <button id='btn' class='claim' onclick='claimNow()'>
        Reclamar Ahora
    </button>

    <div class='timer' id='timer'>
        Disponible ahora
    </div>

    <div class='status' id='msg'></div>

    <div class='small'>
        El sistema guarda tu dirección y solo permite un reclamo cada 24 horas.
        Debes haber minado CHC recientemente.
    </div>

</div>

</div>

<div class='footer'>
Powered by Charly Network • Trust Style UI
</div>

</div>

<script>

let saved = localStorage.getItem("wallet_chc");
if(saved){
    document.getElementById("wallet").value = saved;
}

async function claimNow(){

    let wallet = document.getElementById("wallet").value.trim();

    if(!wallet){
        alert("Pon tu wallet");
        return;
    }

    localStorage.setItem("wallet_chc", wallet);

    document.getElementById("msg").innerHTML = "Procesando...";
    document.getElementById("btn").disabled = true;

    let fd = new FormData();
    fd.append("wallet", wallet);

    let r = await fetch("/claim_bonus",{
        method:"POST",
        body:fd
    });

    let t = await r.text();

    document.getElementById("msg").innerHTML = t;

    if(t.includes("✅")){
        startTimer(86400);
    }else{
        document.getElementById("btn").disabled = false;
    }
}

function startTimer(sec){

    let box = document.getElementById("timer");

    let x = setInterval(()=>{

        sec--;

        let h = Math.floor(sec/3600);
        let m = Math.floor((sec%3600)/60);
        let s = sec%60;

        box.innerHTML =
        h+"h "+m+"m "+s+"s";

        if(sec<=0){
            clearInterval(x);
            box.innerHTML = "Disponible ahora";
            document.getElementById("btn").disabled = false;
        }

    },1000);
}

</script>

</body>
</html>
"""
    return html

# =========================
# INIT
# =========================
if __name__ == "__main__":
    genesis()
    app.run(host="0.0.0.0", port=PORT)
