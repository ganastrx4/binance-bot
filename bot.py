import json
import os
import math
import time
import logging
from binance.client import Client
from binance.enums import *

# Archivo para guardar estado del bot
STATE_FILE = 'bot_state.json'

# Configuración de Binance API
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
client = Client(API_KEY, API_SECRET)

# Parámetros del bot
SYMBOL = 'WLDUSDT'
TARGET_PROFIT = 0.1
LOSS_THRESHOLD = -1
FIBONACCI_SEQUENCE = [1, 1, 2, 3, 5, 8, 13]
WAIT_AFTER_SELL_PERCENT_DROP = 1.5
REENTRADA_PERMITIDA = 1.3  # % caída para reentrar más agresivo

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

# Guardar estado del bot
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

# Cargar estado del bot
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

# Obtener precio actual
def get_price():
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker['price'])

# Actualizar la tendencia del mercado
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

# Obtener cantidad mínima permitida
def get_lot_size(symbol):
    info = client.get_symbol_info(symbol)
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            return float(f['stepSize']), float(f['minQty']), float(f['maxQty'])
    return None, None, None

# Calcular cantidad a comprar
def calculate_quantity(fib_multiplier, price):
    usdt_to_spend = fib_multiplier * TARGET_PROFIT
    usdt_to_spend = max(5.5, min(usdt_to_spend, 6.5))
    quantity = usdt_to_spend / price
    step_size, min_qty, _ = get_lot_size(SYMBOL)
    quantity = math.floor(quantity / step_size) * step_size
    if quantity < min_qty:
        raise ValueError(f"Cantidad {quantity} es menor que mínimo permitido {min_qty}.")
    return round(quantity, 6), usdt_to_spend

# Ejecutar orden de compra o venta
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

# Calcular profit o pérdida
def get_pnl(current_price):
    return (current_price - purchase_price) * current_quantity

# Función principal del bot
def main():
    global purchase_price, current_quantity, current_fib_index
    global last_sell_price, waiting_for_dip, precio_anterior

    load_state()

    while True:
        try:
            current_price = get_price()
            print(f"📈 Precio actual de {SYMBOL}: {current_price:.4f} USDT")

            actualizar_tendencia(current_price)

            if purchase_price > 0:
                pnl = get_pnl(current_price)
                print(f"💰 PNL actual: {pnl:.4f} USDT")

                if pnl >= TARGET_PROFIT:
                    place_order(SIDE_SELL, current_quantity)
                    print("🎯 Vendido con ganancia.")
                    last_sell_price = current_price
                    waiting_for_dip = True
                    purchase_price = 0
                    current_quantity = 0
                    current_fib_index = 0
                    save_state()
                    continue

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
                    print("🔁 Caída detectada. Reentrando...")
                    fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                    new_quantity, _ = calculate_quantity(fib_multiplier, current_price)
                    place_order(SIDE_BUY, new_quantity)
                    purchase_price = current_price
                    current_quantity = new_quantity
                    waiting_for_dip = False
                    save_state()
                    continue
                elif tendencia_actual == "bajando":
                    print("📉 Tendencia bajista. Reentrada inteligente...")
                    fib_multiplier = FIBONACCI_SEQUENCE[current_fib_index]
                    new_quantity, _ = calculate_quantity(fib_multiplier, current_price)
                    place_order(SIDE_BUY, new_quantity)
                    purchase_price = current_price
                    current_quantity = new_quantity
                    waiting_for_dip = False
                    save_state()
                    continue
                else:
                    print(f"⏳ Esperando mejor entrada. Tendencia actual: {tendencia_actual}")

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

