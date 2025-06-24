import json
import os
import math
import time
import logging
import numpy as np
from binance.client import Client
from binance.enums import *

# ---------- CONFIGURACIÓN ----------

STATE_FILE = 'bot_state.json'

API_KEY = 'an460B0AemHRLgbQ5ropCoz8XCm6YqeNp3vNs649A4XgDGcYQ1iIqIIfKwxPb7XN'
API_SECRET = 'ULKGrnpjZItj4VGZbfeoT03ubVPi3ev935m6WcGcO0zBYdzodbjy4KoLDARbFWAV'
client = Client(API_KEY, API_SECRET)

SYMBOL = 'WLDUSDT'
TARGET_PROFIT = 0.1
LOSS_THRESHOLD = -1
FIBONACCI_SEQUENCE = [1, 1, 2, 3, 5, 8, 13]
REENTRADA_PERMITIDA = 0.4  # % caída para reentrar agresivo
MIN_PROFIT_MARGIN = 0.005  # 0.5% para cubrir comisiones y dejar ganancia

# Indicadores
RSI_PERIOD = 14
SMA_PERIOD = 10

# Variables globales
purchase_price = 0
current_fib_index = 0
current_quantity = 0
last_sell_price = 0
waiting_for_dip = False
precio_anterior = 0
tendencia_actual = "estable"
TENDENCIA_BUFFER = []
MAX_BUFFER = 3

# Logging
logging.basicConfig(filename='scalping_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# ---------- FUNCIONES BASE ----------

def save_state():
    state = {
        'purchase_price': purchase_price,
        'current_quantity': current_quantity,
        'current_fib_index': current_fib_index,
        'last_sell_price': last_sell_price,
        'waiting_for_dip': waiting_for_dip
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    global purchase_price, current_quantity, current_fib_index, last_sell_price, waiting_for_dip
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            purchase_price = state.get('purchase_price', 0)
            current_quantity = state.get('current_quantity', 0)
            current_fib_index = state.get('current_fib_index', 0)
            last_sell_price = state.get('last_sell_price', 0)
            waiting_for_dip = state.get('waiting_for_dip', False)

def get_price():
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker['price'])

def get_klines(symbol, interval='1m', limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(k[4]) for k in klines]
    return closes

def calcular_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed > 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calcular_sma(prices, period=10):
    if len(prices) < period:
        return prices[-1]
    return round(sum(prices[-period:]) / period, 4)

def actualizar_tendencia(precio_actual):
    global TENDENCIA_BUFFER, tendencia_actual, precio_anterior
    if precio_anterior == 0:
        precio_anterior = precio_actual
    cambio = precio_actual - precio_anterior
    TENDENCIA_BUFFER.append(cambio)
    if len(TENDENCIA_BUFFER) > MAX_BUFFER:
        TENDENCIA_BUFFER.pop(0)
    promedio = sum(TENDENCIA_BUFFER) / len(TENDENCIA_BUFFER)
    if promedio > 0.01:
        tendencia_actual = "subiendo"
    elif promedio < -0.01:
        tendencia_actual = "bajando"
    else:
        tendencia_actual = "estable"
    precio_anterior = precio_actual
    print(f"📊 Tendencia: {tendencia_actual}")

def get_lot_size(symbol):
    info = client.get_symbol_info(symbol)
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            return float(f['stepSize']), float(f['minQty']), float(f['maxQty'])
    return None, None, None

def calculate_quantity(fib_multiplier, price):
    usdt_to_spend = fib_multiplier * TARGET_PROFIT
    usdt_to_spend = max(5.5, min(usdt_to_spend, 6.5))
    quantity = usdt_to_spend / price
    step_size, min_qty, _ = get_lot_size(SYMBOL)
    quantity = math.floor(quantity / step_size) * step_size
    if quantity < min_qty:
        raise ValueError(f"Cantidad {quantity} es menor que mínimo permitido {min_qty}.")
    return round(quantity, 6), usdt_to_spend

def place_order(side, quantity):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        logging.info(f"Orden {side} ejecutada: {order}")
        print(f"✅ Orden {side} ejecutada: {order}")
        return order
    except Exception as e:
        logging.error(f"Error al colocar orden {side}: {e}")
        print(f"❌ Error al colocar orden {side}: {e}")
        return None

def get_pnl(current_price):
    return (current_price - purchase_price) * current_quantity

# ---------- FUNCION PRINCIPAL ----------

def main():
    global purchase_price, current_quantity, current_fib_index
    global last_sell_price, waiting_for_dip, precio_anterior

    load_state()

    while True:
        try:
            prices = get_klines(SYMBOL)
            current_price = prices[-1]
            sma = calcular_sma(prices, SMA_PERIOD)
            rsi = calcular_rsi(prices, RSI_PERIOD)

            print(f"📈 Precio actual: {current_price:.4f} USDT | SMA: {sma} | RSI: {rsi}")
            actualizar_tendencia(current_price)

            if purchase_price > 0:
                pnl = get_pnl(current_price)
                margen = (current_price - purchase_price) / purchase_price
                print(f"💰 PNL: {pnl:.4f} USDT | Margen: {margen:.4%}")

                if margen >= MIN_PROFIT_MARGIN and tendencia_actual == "bajando":
                    place_order(SIDE_SELL, current_quantity)
                    print("🎯 Vendido con ganancia real. Tendencia bajista detectada.")
                    last_sell_price = current_price
                    waiting_for_dip = True
                    purchase_price = 0
                    current_quantity = 0
                    current_fib_index = 0
                    save_state()
                    continue

                elif margen >= MIN_PROFIT_MARGIN:
                    print("📈 Margen bueno pero tendencia aún alcista. Esperando bajada para vender.")

                elif pnl <= LOSS_THRESHOLD:
                    current_fib_index = min(current_fib_index + 1, len(FIBONACCI_SEQUENCE) - 1)
                    fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                    new_quantity, _ = calculate_quantity(fib_multiplier, current_price * 0.995)
                    print(f"📉 Martingala: Compra {new_quantity}")
                    place_order(SIDE_BUY, new_quantity)
                    purchase_price = current_price * 0.995
                    current_quantity += new_quantity
                    save_state()
                    continue

            elif waiting_for_dip:
                if current_price <= last_sell_price * (1 - REENTRADA_PERMITIDA / 100):
                    print("🔁 Reentrada por caída detectada.")
                    fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                    new_quantity, _ = calculate_quantity(fib_multiplier, current_price)
                    place_order(SIDE_BUY, new_quantity)
                    purchase_price = current_price
                    current_quantity = new_quantity
                    waiting_for_dip = False
                    save_state()
                    continue
                elif tendencia_actual == "bajando" and rsi < 40:
                    print("📉 Reentrada por debilidad confirmada con RSI.")
                    fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                    new_quantity, _ = calculate_quantity(fib_multiplier, current_price)
                    place_order(SIDE_BUY, new_quantity)
                    purchase_price = current_price
                    current_quantity = new_quantity
                    waiting_for_dip = False
                    save_state()
                    continue
                else:
                    print(f"⏳ Esperando mejor entrada. Tendencia: {tendencia_actual} | RSI: {rsi}")

            else:
                fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                new_quantity, _ = calculate_quantity(fib_multiplier, current_price)
                print(f"🟢 Compra inicial: {new_quantity}")
                place_order(SIDE_BUY, new_quantity)
                purchase_price = current_price
                current_quantity = new_quantity
                save_state()

            time.sleep(5)

        except Exception as e:
            logging.error(f"Error en ejecución: {e}")
            print(f"🚨 Error en ejecución: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
