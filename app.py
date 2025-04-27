from flask import Flask, render_template, jsonify
from datetime import datetime
import requests
import hmac
import hashlib
import time
import os
from threading import Thread
import json
import traceback # Para imprimir tracebacks en excepciones

print("--- Script Iniciado ---")

app = Flask(__name__)
# ¡¡¡ADVERTENCIA DE SEGURIDAD!!!
# NO es recomendable tener claves secretas directamente en el código.
# Considera usar variables de entorno.
app.config['SECRET_KEY'] = 'your-secret-key-here-CHANGE-ME' # Cambia esto por una clave segura y única

# Configuración de Binance
BASE_URL = "https://api.binance.com"
ENDPOINT_AD_DETAILS = "/sapi/v1/c2c/merchant/getAdDetails"
# ¡¡¡ADVERTENCIA DE SEGURIDAD!!! Reemplaza con variables de entorno si es posible.
API_KEY = "lvUEV8hkjEbRWlHQj9RCuMyCSCWH6zRHHZltfpSHX395tc4Bwx8HtGsVwtav212U"
SECRET_KEY = "KHrQJ7j2orl5Y9vAb8qwKhJViz3b4ll5WClCtqThPKBEGo6xAU8iGeagaTMhl0SK"

if not API_KEY or not SECRET_KEY:
    print("CRITICAL: ¡Las claves API de Binance no están configuradas!")
    # Considera salir del script si las claves no están:
    # import sys
    # sys.exit("Error: Claves API no configuradas.")

# Estado global para almacenar datos
estado_global = {}
precio_btc_actual = 0.0

MERCHANTS = [
    "sf50ee1a424f832dfad73f9db737dccfc",   # Bachat4King
    "sbc15d4c70a3a3a08a34930c43d56c2d0",   # LuchoTrade
    "sf3e5fd4e979534a98f3eebcaa6a98b98",   # Pabl1toesteban
    # ... (resto de los merchants igual que antes) ...
    "s648e45a6be1539ffaa7bf5fe462dd0ca",   # InterserviceSpa
    "s9dccdd3004963f2d9d6d7b7cb0ae90b2",   # Vultur_SpA
]
print(f"INFO: Lista de {len(MERCHANTS)} merchants cargada.")
if len(MERCHANTS) != len(set(MERCHANTS)):
    print("WARNING: ¡Se detectaron IDs de merchant duplicados en la lista MERCHANTS!")


def generate_signature(query_string):
    # print(f"DEBUG: Generando firma para query_string: {query_string}") # Descomentar si necesitas depurar firma
    return hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_headers():
    # print(f"DEBUG: Generando cabeceras con API Key: {API_KEY[:5]}...") # No mostrar la clave completa
    return {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }

def obtener_detalles_usuario(merchant_no):
    timestamp_req = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp_req}] API_CALL_START: Obtener detalles para {merchant_no}")
    try:
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}&merchantNo={merchant_no}"
        signature = generate_signature(query_string)
        query_string_signed = f"{query_string}&signature={signature}"
        url = f"{BASE_URL}{ENDPOINT_AD_DETAILS}?{query_string_signed}"
        headers = get_headers()

        response = requests.get(url, headers=headers, timeout=20)
        timestamp_res = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp_res}] API_CALL_END: Respuesta para {merchant_no}. Status: {response.status_code}")

        if response.status_code != 200:
             print(f"ERROR: Petición fallida para {merchant_no}. Status Code: {response.status_code}. Respuesta: {response.text}")
             return {"error": f"Error HTTP {response.status_code}", "details": response.text}

        try:
            data = response.json()
            # print(f"DEBUG: Datos JSON recibidos para {merchant_no}: {json.dumps(data, indent=2)}") # Descomentar si necesitas ver el JSON
        except json.JSONDecodeError:
            print(f"ERROR: Error al decodificar JSON para {merchant_no}. Respuesta: {response.text}")
            traceback.print_exc() # Imprime el traceback del error JSON
            return {"error": "Respuesta inválida (no es JSON)", "details": response.text}

        if not data.get("success", False):
            error_msg = data.get("message", "Sin mensaje de error específico")
            error_code = data.get("code", "N/A")
            print(f"ERROR: Respuesta API Binance no exitosa para {merchant_no}. Code: {error_code}, Message: {error_msg}. Data: {data}")
            return {"error": f"Error API Binance: {error_msg} (Code: {error_code})"}

        if "data" not in data or not data["data"] or "merchant" not in data["data"] or not data["data"]["merchant"]:
             print(f"ERROR: Formato de respuesta inesperado para {merchant_no}. Falta 'data' o 'merchant'. Data: {data}")
             return {"error": "Formato de respuesta inesperado", "details": data}

        merchant = data["data"]["merchant"]
        stats = merchant.get("userStatsResp")

        if not stats:
            print(f"ERROR: No se encontraron 'userStatsResp' para {merchant_no}. Merchant data: {merchant}")
            return {"error": "Faltan estadísticas del usuario ('userStatsResp')", "details": merchant}

        detalles = {
            "nick": merchant.get("nickName", "Desconocido"),
            "compras": int(stats.get("completedBuyOrderNumOfLatest30day", 0)),
            "ventas": int(stats.get("completedSellOrderNumOfLatest30day", 0)),
            "btc_compras": float(stats.get("completedBuyOrderTotalBtcAmount", 0.0)),
            "btc_ventas": float(stats.get("completedSellOrderTotalBtcAmount", 0.0))
        }
        print(f"INFO: Detalles obtenidos OK para {merchant_no}: Nick={detalles['nick']}")
        return detalles

    except requests.exceptions.RequestException as req_err:
        print(f"ERROR: Excepción de Requests al obtener detalles para {merchant_no}: {req_err}")
        traceback.print_exc()
        return {"error": f"Error de red/HTTP: {str(req_err)}"}
    except Exception as e:
        print(f"ERROR: Excepción inesperada al obtener detalles para {merchant_no}: {e}")
        traceback.print_exc() # Imprime el traceback completo
        return {"error": f"Error inesperado en obtener_detalles_usuario: {str(e)}"}

def obtener_precio_btc_usdt():
    timestamp_req = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp_req}] API_CALL_START: Obtener precio BTC/USDT")
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url, timeout=10)
        timestamp_res = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp_res}] API_CALL_END: Respuesta precio BTC/USDT. Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        precio = float(data["price"])
        print(f"INFO: Precio BTC/USDT obtenido: {precio}")
        return precio
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR: Excepción de Requests al obtener precio BTC/USDT: {req_err}")
        traceback.print_exc()
        return 0.0
    except (KeyError, ValueError, json.JSONDecodeError) as parse_err:
         print(f"ERROR: Error al parsear respuesta de precio BTC/USDT: {parse_err}. Respuesta: {response.text if 'response' in locals() else 'N/A'}")
         traceback.print_exc()
         return 0.0
    except Exception as e:
        print(f"ERROR: Excepción inesperada al obtener precio BTC/USDT: {e}")
        traceback.print_exc()
        return 0.0

def actualizar_datos():
    global estado_global, precio_btc_actual
    print("INFO: Iniciando bucle de actualización de datos...")
    while True:
        print(f"\n----- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Inicio de ciclo de actualización -----")
        precio_btc_actual = obtener_precio_btc_usdt()
        if precio_btc_actual == 0.0:
            print("WARNING: No se pudo obtener el precio de BTC/USDT en este ciclo.")

        processed_merchants = 0
        for merchant in MERCHANTS:
            # print(f"DEBUG: Procesando merchant: {merchant}") # Descomentar si necesitas ver cada merchant
            detalles = obtener_detalles_usuario(merchant)

            if "error" in detalles:
                print(f"ERROR_DETAIL: Error al obtener detalles para {merchant}: {detalles['error']}. Detalles: {detalles.get('details', 'N/A')}")
                time.sleep(1)
                continue

            processed_merchants += 1

            if merchant not in estado_global:
                print(f"INFO: Inicializando estado para nuevo merchant: {merchant} ({detalles['nick']})")
                estado_global[merchant] = {
                    "nick": detalles["nick"],
                    "compras_base": detalles["compras"],
                    "ventas_base": detalles["ventas"],
                    "btc_compra_base": detalles["btc_compras"],
                    "btc_venta_base": detalles["btc_ventas"],
                    "compras_total": 0,
                    "ventas_total": 0,
                    "hora_ultima_compra": "--:--",
                    "hora_ultima_venta": "--:--",
                    "btc_ultima_compra": 0.0,
                    "btc_ultima_venta": 0.0,
                    "usdt_acumulado_compra": 0.0,
                    "usdt_acumulado_venta": 0.0,
                    "timestamp_last_update": datetime.now().isoformat()
                }

            estado = estado_global[merchant]
            comp_act = detalles["compras"]
            vent_act = detalles["ventas"]
            btc_comp_act = detalles["btc_compras"]
            btc_vent_act = detalles["btc_ventas"]
            timestamp_actual = datetime.now()

            # --- Lógica de Compras ---
            if comp_act >= estado["compras_base"]:
                nuevas_compras_detectadas = comp_act - estado["compras_base"]
                if nuevas_compras_detectadas > estado["compras_total"]:
                    num_nuevas = nuevas_compras_detectadas - estado["compras_total"]
                    delta_btc = round(btc_comp_act - estado["btc_compra_base"], 8)
                    delta_usdt = round(delta_btc * precio_btc_actual, 2) if precio_btc_actual else 0.0
                    hora_actual_str = timestamp_actual.strftime("%H:%M:%S") # Incluye segundos para más precisión

                    print(f"************************************************************")
                    print(f"*** ¡CAMBIO DETECTADO (COMPRA)! Merchant: {merchant} ({estado['nick']}) [{hora_actual_str}] ***")
                    print(f"   - Cantidad Nueva(s): {num_nuevas} (Total relativo: {nuevas_compras_detectadas})")
                    print(f"   - Delta BTC: {delta_btc:.8f}")
                    print(f"   - Delta USDT (aprox): {delta_usdt:.2f} (Precio BTC: {precio_btc_actual})")
                    print(f"   - Stats API: Compras={comp_act}, BTC={btc_comp_act:.8f}")
                    print(f"   - Estado Anterior: Total={estado['compras_total']}, BTC Base={estado['btc_compra_base']:.8f}")
                    print(f"************************************************************")


                    estado["compras_total"] = nuevas_compras_detectadas
                    estado["hora_ultima_compra"] = timestamp_actual.strftime("%H:%M") # Mantenemos H:M para la UI
                    estado["btc_ultima_compra"] = delta_btc
                    estado["btc_compra_base"] = btc_comp_act
                    estado["usdt_acumulado_compra"] += delta_usdt
                # Añadir lógica para manejar advertencias si es necesario (compras < total previo)

            # --- Lógica de Ventas ---
            if vent_act >= estado["ventas_base"]:
                nuevas_ventas_detectadas = vent_act - estado["ventas_base"]
                if nuevas_ventas_detectadas > estado["ventas_total"]:
                    num_nuevas = nuevas_ventas_detectadas - estado["ventas_total"]
                    delta_btc = round(btc_vent_act - estado["btc_venta_base"], 8)
                    delta_usdt = round(delta_btc * precio_btc_actual, 2) if precio_btc_actual else 0.0
                    hora_actual_str = timestamp_actual.strftime("%H:%M:%S")

                    print(f"************************************************************")
                    print(f"*** ¡CAMBIO DETECTADO (VENTA)! Merchant: {merchant} ({estado['nick']}) [{hora_actual_str}] ***")
                    print(f"   - Cantidad Nueva(s): {num_nuevas} (Total relativo: {nuevas_ventas_detectadas})")
                    print(f"   - Delta BTC: {delta_btc:.8f}")
                    print(f"   - Delta USDT (aprox): {delta_usdt:.2f} (Precio BTC: {precio_btc_actual})")
                    print(f"   - Stats API: Ventas={vent_act}, BTC={btc_vent_act:.8f}")
                    print(f"   - Estado Anterior: Total={estado['ventas_total']}, BTC Base={estado['btc_venta_base']:.8f}")
                    print(f"************************************************************")

                    estado["ventas_total"] = nuevas_ventas_detectadas
                    estado["hora_ultima_venta"] = timestamp_actual.strftime("%H:%M")
                    estado["btc_ultima_venta"] = delta_btc
                    estado["btc_venta_base"] = btc_vent_act
                    estado["usdt_acumulado_venta"] += delta_usdt
                # Añadir lógica para manejar advertencias si es necesario (ventas < total previo)

            estado["timestamp_last_update"] = timestamp_actual.isoformat()
            time.sleep(0.5) # Pausa entre merchants

        print(f"----- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fin de ciclo. Merchants OK: {processed_merchants}/{len(MERCHANTS)} -----")
        sleep_time = 30
        # print(f"DEBUG: Esperando {sleep_time} segundos...") # Descomentar si necesitas ver la espera
        time.sleep(sleep_time)

@app.route('/')
def index():
    # print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Request: Ruta '/'") # Descomentar si necesitas log de rutas
    return render_template('index.html')

@app.route('/api/datos')
def get_datos():
    # print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Request: Ruta '/api/datos'") # Descomentar si necesitas log de rutas
    estado_actual = estado_global.copy()
    datos_respuesta = {
        'estado': estado_actual,
        'precio_btc': precio_btc_actual,
        'hora_actual': datetime.now().strftime("%H:%M"),
        'fecha_actual': datetime.now().strftime("%d %B")
    }
    return jsonify(datos_respuesta)

if __name__ == '__main__':
    print("INFO: Configurando y iniciando servidor Flask y hilo de actualización...")
    thread = Thread(target=actualizar_datos, daemon=True, name="UpdateThread")
    thread.start()
    print("INFO: Hilo de actualización iniciado.")

    port = int(os.environ.get('PORT', 5000))
    print(f"INFO: Iniciando servidor Flask en host 0.0.0.0 puerto {port}")
    # Ejecutar con debug=False para producción
    # Considerar usar 'waitress' o 'gunicorn': pip install waitress; waitress-serve --host=0.0.0.0 --port=5000 tu_archivo:app
    app.run(host='0.0.0.0', port=port, debug=False)
