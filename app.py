from flask import Flask, render_template, jsonify
from datetime import datetime
import requests
import hmac
import hashlib
import time
import os
from threading import Thread
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Configuración de Binance
BASE_URL = "https://api.binance.com"
ENDPOINT_AD_DETAILS = "/sapi/v1/c2c/merchant/getAdDetails"
API_KEY = "lvUEV8hkjEbRWlHQj9RCuMyCSCWH6zRHHZltfpSHX395tc4Bwx8HtGsVwtav212U"
SECRET_KEY = "KHrQJ7j2orl5Y9vAb8qwKhJViz3b4ll5WClCtqThPKBEGo6xAU8iGeagaTMhl0SK"

# Estado global para almacenar datos
estado_global = {}
precio_btc_actual = 0.0

MERCHANTS = [
    "sf50ee1a424f832dfad73f9db737dccfc",   # Bachat4King 
    "sbc15d4c70a3a3a08a34930c43d56c2d0",   # LuchoTrade 
    "sf3e5fd4e979534a98f3eebcaa6a98b98",   # Pabl1toesteban 
    "s61e7483a655c3f4fbed0eea664a6d783",   # cryptonft 
    "s05a86dd0e2c732c8a858fbf43ee762db",   # CAPITAL-PAYMENT 
    "sa386b60ffd963113bddc995ca220e462",   # koraySpa   
    "sd59cf0cfa32138a0b847d3b1ead1229e",   # BEXCRYPT0
    "s1dcd7a14c945375fadc8e5a22f085a49",   # Moneymaker
    "se16fcb072ac033a1b202cc1a63dd0bec",   # DLPZ
    "sd9a45f920a4d3bdfba7fec4a80b47637",   # tscapitalchile
    "s006f3d5ac59f3efab63ce51b2d0dca69",   # thanthos01
    "s8ac9a1ff9be73dfdbfb28fe880004a92",   # JD-CAPITALHOLDING
    "sddec785a008533bda7349454d120710a",   # INVERSIONES_MANA
    "sda33c943018033098ed202456dc93ff1",   # CRYPTOMARKET
    "s9b7dcd366be434e2b748258ed0f78515",   # F-Malejandro
    "s3a0ec258bb8a32bcac0ba5a5d7b49b93",   # CysDigitalSpa
    "s5ff472f833863e63a5d2f270933f45c6",   # PUPISPA
    "s75696a0dab0f3ace8448e033fec362c1",   # inversionesbyrlimita
    "sce481a1037133f15a757a3096b2be0db",   # Las3JSPAexchange
    "s5213f8588c4137e1bd6c6394cb99784b",   # Ahuman_
    "se5b2469eed2732cd81c3ba51cdfed8b3",   # josero80
    "s4bd5fcce3c783ba98c12a4c71922a410",   # MatGer
    "sd50e897a309e3c578b132471fe846545",   # BUYSELL-USDT_COM
    "s2ac6b59a1e0d31b99aea7c61acde56a2",   # SuffoSPA
    "sf79cb640b5643b3bab7cf7e7e081f7d3",   # San Cristóbal SPA
    "sd146ee1b20d53eca91f9c462ceb90efc",   # ArsoCrypto_spa1
    "s9fb8c738832b369c90eb0b0806e6c350",   # CSalcedoi
    "se3829be15739316b980a80966ed1e9c5",   # TeltonSPA_Titular
    "s6f987c71195930a4a8555d98b2e95c9f",   # SuBit-SpA
    "s6f987c71195930a4a8555d98b2e95c9f",   # CriptoZona
    "s1b79bb9379793c7fa5750ae984aae227",   # AgusExchange
    "s819cba7547bc3494b04afb6e46ec3ecc",   # RIVPAY
    "sde3dd78c7f1e39f7814bc57c57dd3e99",   # TakemichiOutlaw
    "sb1a9b38c29233745aa6b5ee9264b6dca",   # SGroup
    "s3cffdef83e1231afb3a3599e2850481a",   # Vanher-CapitalChile
    "s81303dab476d30a28d6b9240937fcda7",   # Payservi2
    "s648e45a6be1539ffaa7bf5fe462dd0ca",   # InterserviceSpa
    "s9dccdd3004963f2d9d6d7b7cb0ae90b2",   # Vultur_SpA
]

def generate_signature(query_string):
    print(f"[DEBUG] Generando firma para query_string: {query_string}")
    return hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_headers():
    return {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }

def obtener_detalles_usuario(merchant_no):
    try:
        print(f"[INFO] Obteniendo detalles para merchant: {merchant_no}")
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}&merchantNo={merchant_no}"
        signature = generate_signature(query_string)
        query_string += f"&signature={signature}"
        
        url = f"{BASE_URL}{ENDPOINT_AD_DETAILS}?{query_string}"
        print(f"[DEBUG] Realizando petición a: {url}")
        
        response = requests.get(url, headers=get_headers(), timeout=10)
        print(f"[DEBUG] Respuesta recibida: {response.status_code}")
        
        data = response.json()
        print(f"[DEBUG] Datos recibidos: {json.dumps(data, indent=2)}")

        if not data.get("success", False):
            print(f"[ERROR] Error en respuesta del servidor para merchant {merchant_no}: {data}")
            return {"error": "Error en respuesta del servidor"}

        merchant = data["data"]["merchant"]
        stats = merchant["userStatsResp"]

        resultado = {
            "nick": merchant.get("nickName", "Desconocido"),
            "compras": int(stats["completedBuyOrderNumOfLatest30day"]),
            "ventas": int(stats["completedSellOrderNumOfLatest30day"]),
            "btc_compras": float(stats["completedBuyOrderTotalBtcAmount"]),
            "btc_ventas": float(stats["completedSellOrderTotalBtcAmount"])
        }
        print(f"[INFO] Detalles obtenidos exitosamente para {resultado['nick']}: {json.dumps(resultado, indent=2)}")
        return resultado
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión para merchant {merchant_no}: {str(e)}")
        return {"error": "Sin conexión a internet"}
    except Exception as e:
        print(f"[ERROR] Error inesperado para merchant {merchant_no}: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        return {"error": f"Error inesperado: {str(e)}"}

def obtener_precio_btc_usdt():
    try:
        print("[DEBUG] Obteniendo precio actual de BTC/USDT")
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=10)
        data = response.json()
        precio = float(data["price"])
        print(f"[INFO] Precio BTC/USDT actualizado: {precio}")
        return precio
    except Exception as e:
        print(f"[ERROR] Error al obtener precio BTC/USDT: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        return 0.0

def actualizar_datos():
    global estado_global, precio_btc_actual
    print("[INFO] Iniciando ciclo de actualización de datos")
    while True:
        try:
            precio_btc_actual = obtener_precio_btc_usdt()
            print(f"[DEBUG] Procesando {len(MERCHANTS)} merchants con precio BTC: {precio_btc_actual}")
            
            for merchant in MERCHANTS:
                detalles = obtener_detalles_usuario(merchant)
                if "error" not in detalles:
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
                    
                    estado = estado_global[merchant]
                    comp_act = detalles["compras"]
                    vent_act = detalles["ventas"]
                    btc_comp = detalles["btc_compras"]
                    btc_vent = detalles["btc_ventas"]

                    diff_c = comp_act - estado["compras_base"]
                    diff_v = vent_act - estado["ventas_base"]

                    if diff_c > estado["compras_total"]:
                        delta_btc = round(btc_comp - estado["btc_compra_base"], 6)
                        delta_usdt = delta_btc * precio_btc_actual
                        print(f"[INFO] Nueva compra detectada para {estado['nick']}: {delta_btc} BTC ({delta_usdt} USDT)")
                        estado["compras_total"] += (diff_c - estado["compras_total"])
                        estado["hora_ultima_compra"] = datetime.now().strftime("%H:%M")
                        estado["btc_ultima_compra"] = delta_btc
                        estado["btc_compra_base"] = btc_comp
                        estado["usdt_acumulado_compra"] += delta_usdt

                    if diff_v > estado["ventas_total"]:
                        delta_btc = round(btc_vent - estado["btc_venta_base"], 6)
                        delta_usdt = delta_btc * precio_btc_actual
                        print(f"[INFO] Nueva venta detectada para {estado['nick']}: {delta_btc} BTC ({delta_usdt} USDT)")
                        estado["ventas_total"] += (diff_v - estado["ventas_total"])
                        estado["hora_ultima_venta"] = datetime.now().strftime("%H:%M")
                        estado["btc_ultima_venta"] = delta_btc
                        estado["btc_venta_base"] = btc_vent
                        estado["usdt_acumulado_venta"] += delta_usdt
                else:
                    print(f"[ERROR] Error al procesar merchant {merchant}: {detalles['error']}")

            print("[DEBUG] Ciclo de actualización completado, esperando 30 segundos...")
            time.sleep(30)
            
        except Exception as e:
            print(f"[ERROR] Error en ciclo de actualización: {str(e)}")
            import traceback
            print(f"[ERROR] Stack trace: {traceback.format_exc()}")
            time.sleep(30)  # Esperar antes de reintentar

@app.route('/')
def index():
    print("[DEBUG] Acceso a la página principal")
    return render_template('index.html')

@app.route('/api/datos')
def get_datos():
    print("[DEBUG] Solicitud de datos recibida")
    return jsonify({
        'estado': estado_global,
        'precio_btc': precio_btc_actual,
        'hora_actual': datetime.now().strftime("%H:%M"),
        'fecha_actual': datetime.now().strftime("%d %B")
    })

if __name__ == '__main__':
    print("[INFO] Iniciando aplicación...")
    thread = Thread(target=actualizar_datos, daemon=True)
    thread.start()
    print("[INFO] Thread de actualización iniciado")

    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Servidor iniciando en puerto {port}")
    app.run(host='0.0.0.0', port=port)