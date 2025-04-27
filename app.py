from flask import Flask, render_template, jsonify
from datetime import datetime
import requests
import hmac
import hashlib
import time
import os
from threading import Thread, Lock
import json
import traceback # Para imprimir tracebacks en excepciones

print("--- Script Iniciado ---")

app = Flask(__name__)
# ¡¡¡ADVERTENCIA DE SEGURIDAD!!!
# NO es recomendable tener claves secretas directamente en el código.
# Considera usar variables de entorno.
app.config['SECRET_KEY'] = '123456789qwerty' # Cambia esto por una clave segura y única

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
estado_lock = Lock()  # Lock para proteger el acceso al estado global
thread_activo = False  # Flag para controlar el estado del thread

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
    print(f"[DEBUG] Generando firma para query_string: {query_string}")
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    print(f"[DEBUG] Firma generada: {signature[:10]}...")
    return signature

def get_headers():
    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }
    print(f"[DEBUG] Headers generados: {headers}")
    return headers

def obtener_detalles_usuario(merchant_no):
    try:
        print(f"\n[INFO] {'='*50}")
        print(f"[INFO] Iniciando obtención de detalles para merchant: {merchant_no}")
        print(f"[INFO] {'='*50}")
        
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}&merchantNo={merchant_no}"
        print(f"[DEBUG] Query string inicial: {query_string}")
        
        signature = generate_signature(query_string)
        query_string += f"&signature={signature}"
        print(f"[DEBUG] Query string final: {query_string}")
        
        url = f"{BASE_URL}{ENDPOINT_AD_DETAILS}?{query_string}"
        print(f"[DEBUG] URL completa: {url}")
        
        print("[DEBUG] Realizando petición HTTP...")
        print(f"[DEBUG] Headers enviados: {get_headers()}")
        response = requests.get(url, headers=get_headers(), timeout=10)
        print(f"[DEBUG] Código de respuesta: {response.status_code}")
        print(f"[DEBUG] Headers de respuesta: {dict(response.headers)}")
        print(f"[DEBUG] Contenido de respuesta: {response.text[:500]}...")  # Primeros 500 caracteres
        
        data = response.json()
        print(f"[DEBUG] Datos recibidos: {json.dumps(data, indent=2)}")

        if not data.get("success", False):
            print(f"[ERROR] Error en respuesta del servidor para merchant {merchant_no}")
            print(f"[ERROR] Datos de error: {data}")
            return {"error": "Error en respuesta del servidor"}

        merchant = data["data"]["merchant"]
        stats = merchant["userStatsResp"]
        print(f"[DEBUG] Datos del merchant: {json.dumps(merchant, indent=2)}")
        print(f"[DEBUG] Estadísticas: {json.dumps(stats, indent=2)}")

        resultado = {
            "nick": merchant.get("nickName", "Desconocido"),
            "compras": int(stats["completedBuyOrderNumOfLatest30day"]),
            "ventas": int(stats["completedSellOrderNumOfLatest30day"]),
            "btc_compras": float(stats["completedBuyOrderTotalBtcAmount"]),
            "btc_ventas": float(stats["completedSellOrderTotalBtcAmount"])
        }
        print(f"[INFO] Resultado procesado: {json.dumps(resultado, indent=2)}")
        print(f"[INFO] {'='*50}\n")
        return resultado
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión para merchant {merchant_no}")
        print(f"[ERROR] Detalles del error: {str(e)}")
        print(f"[ERROR] {'='*50}\n")
        return {"error": "Sin conexión a internet"}
    except Exception as e:
        print(f"[ERROR] Error inesperado para merchant {merchant_no}")
        print(f"[ERROR] Tipo de error: {type(e).__name__}")
        print(f"[ERROR] Mensaje de error: {str(e)}")
        print("[ERROR] Stack trace completo:")
        print(traceback.format_exc())
        print(f"[ERROR] {'='*50}\n")
        return {"error": f"Error inesperado: {str(e)}"}

def obtener_precio_btc_usdt():
    try:
        print("\n[INFO] Iniciando obtención de precio BTC/USDT")
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        print(f"[DEBUG] URL: {url}")
        
        print("[DEBUG] Realizando petición HTTP...")
        response = requests.get(url, timeout=10)
        print(f"[DEBUG] Código de respuesta: {response.status_code}")
        print(f"[DEBUG] Headers de respuesta: {dict(response.headers)}")
        print(f"[DEBUG] Contenido de respuesta: {response.text}")
        
        data = response.json()
        print(f"[DEBUG] Datos recibidos: {json.dumps(data, indent=2)}")
        
        precio = float(data["price"])
        print(f"[INFO] Precio BTC/USDT actualizado: {precio}")
        print("[INFO] Obtención de precio completada\n")
        return precio
    except Exception as e:
        print("[ERROR] Error al obtener precio BTC/USDT")
        print(f"[ERROR] Tipo de error: {type(e).__name__}")
        print(f"[ERROR] Mensaje de error: {str(e)}")
        print("[ERROR] Stack trace completo:")
        print(traceback.format_exc())
        print("[ERROR] Fin del error\n")
        return 0.0

def actualizar_datos():
    global estado_global, precio_btc_actual, thread_activo
    print("\n[INFO] Iniciando ciclo de actualización de datos")
    ciclo = 1
    thread_activo = True
    
    while thread_activo:
        try:
            print(f"\n[INFO] {'='*50}")
            print(f"[INFO] Inicio del ciclo #{ciclo}")
            print(f"[INFO] {'='*50}")
            
            print("[DEBUG] Intentando obtener precio BTC/USDT...")
            nuevo_precio = obtener_precio_btc_usdt()
            print(f"[DEBUG] Nuevo precio obtenido: {nuevo_precio}")
            
            with estado_lock:
                precio_btc_actual = nuevo_precio
                print(f"[DEBUG] Precio actualizado en estado global: {precio_btc_actual}")
            
            print(f"[DEBUG] Procesando {len(MERCHANTS)} merchants con precio BTC: {precio_btc_actual}")
            
            for i, merchant in enumerate(MERCHANTS, 1):
                print(f"\n[INFO] Procesando merchant {i}/{len(MERCHANTS)}: {merchant}")
                print("[DEBUG] Intentando obtener detalles del merchant...")
                detalles = obtener_detalles_usuario(merchant)
                
                if "error" not in detalles:
                    print("[DEBUG] Detalles obtenidos exitosamente")
                    with estado_lock:
                        if merchant not in estado_global:
                            print(f"[INFO] Inicializando estado para nuevo merchant: {detalles['nick']}")
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
                                "usdt_acumulado_venta": 0.0
                            }
                            print(f"[DEBUG] Estado inicial: {json.dumps(estado_global[merchant], indent=2)}")
                        
                        estado = estado_global[merchant]
                        comp_act = detalles["compras"]
                        vent_act = detalles["ventas"]
                        btc_comp = detalles["btc_compras"]
                        btc_vent = detalles["btc_ventas"]

                        print(f"[DEBUG] Valores actuales para {estado['nick']}:")
                        print(f"  - Compras: {comp_act} (base: {estado['compras_base']})")
                        print(f"  - Ventas: {vent_act} (base: {estado['ventas_base']})")
                        print(f"  - BTC compras: {btc_comp} (base: {estado['btc_compra_base']})")
                        print(f"  - BTC ventas: {btc_vent} (base: {estado['btc_venta_base']})")

                        diff_c = comp_act - estado["compras_base"]
                        diff_v = vent_act - estado["ventas_base"]

                        print(f"[DEBUG] Diferencias detectadas:")
                        print(f"  - Compras: {diff_c}")
                        print(f"  - Ventas: {diff_v}")

                        if diff_c > estado["compras_total"]:
                            delta_btc = round(btc_comp - estado["btc_compra_base"], 6)
                            delta_usdt = delta_btc * precio_btc_actual
                            print(f"[INFO] Nueva compra detectada para {estado['nick']}:")
                            print(f"  - Delta BTC: {delta_btc}")
                            print(f"  - Delta USDT: {delta_usdt}")
                            
                            estado["compras_total"] += (diff_c - estado["compras_total"])
                            estado["hora_ultima_compra"] = datetime.now().strftime("%H:%M")
                            estado["btc_ultima_compra"] = delta_btc
                            estado["btc_compra_base"] = btc_comp
                            estado["usdt_acumulado_compra"] += delta_usdt
                            
                            print(f"[DEBUG] Estado actualizado después de compra: {json.dumps(estado, indent=2)}")

                        if diff_v > estado["ventas_total"]:
                            delta_btc = round(btc_vent - estado["btc_venta_base"], 6)
                            delta_usdt = delta_btc * precio_btc_actual
                            print(f"[INFO] Nueva venta detectada para {estado['nick']}:")
                            print(f"  - Delta BTC: {delta_btc}")
                            print(f"  - Delta USDT: {delta_usdt}")
                            
                            estado["ventas_total"] += (diff_v - estado["ventas_total"])
                            estado["hora_ultima_venta"] = datetime.now().strftime("%H:%M")
                            estado["btc_ultima_venta"] = delta_btc
                            estado["btc_venta_base"] = btc_vent
                            estado["usdt_acumulado_venta"] += delta_usdt
                            
                            print(f"[DEBUG] Estado actualizado después de venta: {json.dumps(estado, indent=2)}")
                else:
                    print(f"[ERROR] Error al procesar merchant {merchant}: {detalles['error']}")

            print(f"[INFO] Ciclo #{ciclo} completado")
            print(f"[INFO] Estado actual del sistema:")
            with estado_lock:
                print(f"  - Precio BTC: {precio_btc_actual}")
                print(f"  - Merchants activos: {len(estado_global)}")
                print(f"  - Estado global: {json.dumps(estado_global, indent=2)}")
            print(f"[INFO] Esperando 30 segundos antes del siguiente ciclo...")
            ciclo += 1
            time.sleep(30)
            
        except Exception as e:
            print("[ERROR] Error en ciclo de actualización")
            print(f"[ERROR] Tipo de error: {type(e).__name__}")
            print(f"[ERROR] Mensaje de error: {str(e)}")
            print("[ERROR] Stack trace completo:")
            print(traceback.format_exc())
            print("[ERROR] Esperando 30 segundos antes de reintentar...")
            time.sleep(30)

@app.route('/')
def index():
    print("[DEBUG] Acceso a la página principal")
    return render_template('index.html')

@app.route('/api/datos')
def get_datos():
    print("[DEBUG] Solicitud de datos recibida")
    with estado_lock:
        datos = {
            'estado': estado_global,
            'precio_btc': precio_btc_actual,
            'hora_actual': datetime.now().strftime("%H:%M"),
            'fecha_actual': datetime.now().strftime("%d %B")
        }
    print(f"[DEBUG] Datos a enviar: {json.dumps(datos, indent=2)}")
    return jsonify(datos)

if __name__ == '__main__':
    print("\n[INFO] Iniciando aplicación...")
    thread = Thread(target=actualizar_datos, daemon=True)
    thread.start()
    print("[INFO] Thread de actualización iniciado")

    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Servidor iniciando en puerto {port}")
    app.run(host='0.0.0.0', port=port)