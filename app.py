from flask import Flask, render_template, jsonify
from datetime import datetime
import requests
import hmac
import hashlib
import time
import os
from threading import Thread
import json
import logging # <-- Añadido
import sys # <-- Añadido

# --- Configuración de Logging ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s')
log_handler_file = logging.FileHandler('app.log', mode='a') # Log a archivo app.log
log_handler_file.setFormatter(log_formatter)
log_handler_console = logging.StreamHandler(sys.stdout) # Log a consola
log_handler_console.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Nivel DEBUG para máxima verbosidad
logger.addHandler(log_handler_file)
logger.addHandler(log_handler_console)
logger.propagate = False # Evita duplicar logs si el logger raíz ya está configurado

# --- Fin Configuración de Logging ---

logger.info("Iniciando la aplicación Flask...")

app = Flask(__name__)
# ¡¡¡ADVERTENCIA DE SEGURIDAD!!!
# NO es recomendable tener claves secretas directamente en el código.
# Considera usar variables de entorno. Ejemplo:
# app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key-if-not-set')
# API_KEY = os.environ.get('BINANCE_API_KEY')
# SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY')
# Si no puedes usar variables de entorno, asegúrate de que este archivo no sea público.
app.config['SECRET_KEY'] = 'your-secret-key-here' # Cambia esto por una clave segura y única

# Configuración de Binance
BASE_URL = "https://api.binance.com"
ENDPOINT_AD_DETAILS = "/sapi/v1/c2c/merchant/getAdDetails"
# ¡¡¡ADVERTENCIA DE SEGURIDAD!!! Reemplaza con variables de entorno si es posible.
API_KEY = "lvUEV8hkjEbRWlHQj9RCuMyCSCWH6zRHHZltfpSHX395tc4Bwx8HtGsVwtav212U"
SECRET_KEY = "KHrQJ7j2orl5Y9vAb8qwKhJViz3b4ll5WClCtqThPKBEGo6xAU8iGeagaTMhl0SK"

# Validar que las claves API estén presentes (básico)
if not API_KEY or not SECRET_KEY:
    logger.critical("¡Las claves API de Binance no están configuradas!")
    # Podrías querer salir o manejar esto de forma más robusta
    # sys.exit("Error: Claves API no configuradas.")

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
    "s6f987c71195930a4a8555d98b2e95c9f",   # SuBit-SpA  <- ID Repetido? Verificar si es correcto
    "s6f987c71195930a4a8555d98b2e95c9f",   # CriptoZona <- ID Repetido? Verificar si es correcto
    "s1b79bb9379793c7fa5750ae984aae227",   # AgusExchange
    "s819cba7547bc3494b04afb6e46ec3ecc",   # RIVPAY
    "sde3dd78c7f1e39f7814bc57c57dd3e99",   # TakemichiOutlaw
    "sb1a9b38c29233745aa6b5ee9264b6dca",   # SGroup
    "s3cffdef83e1231afb3a3599e2850481a",   # Vanher-CapitalChile
    "s81303dab476d30a28d6b9240937fcda7",   # Payservi2
    "s648e45a6be1539ffaa7bf5fe462dd0ca",   # InterserviceSpa
    "s9dccdd3004963f2d9d6d7b7cb0ae90b2",   # Vultur_SpA
]
logger.info(f"Lista de {len(MERCHANTS)} merchants cargada.")
# Verificar IDs duplicados
if len(MERCHANTS) != len(set(MERCHANTS)):
    logger.warning("¡Se detectaron IDs de merchant duplicados en la lista MERCHANTS!")

def generate_signature(query_string):
    logger.debug(f"Generando firma para query_string: {query_string}")
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    logger.debug(f"Firma generada: {signature}")
    return signature

def get_headers():
    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }
    logger.debug(f"Generando cabeceras: {headers}") # No loguear API Key completa en producción si es posible
    return headers

def obtener_detalles_usuario(merchant_no):
    logger.debug(f"Intentando obtener detalles para merchant: {merchant_no}")
    try:
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}&merchantNo={merchant_no}"
        signature = generate_signature(query_string)
        query_string_signed = f"{query_string}&signature={signature}"
        url = f"{BASE_URL}{ENDPOINT_AD_DETAILS}?{query_string_signed}"
        headers = get_headers()

        logger.info(f"Realizando petición GET a: {BASE_URL}{ENDPOINT_AD_DETAILS}")
        logger.debug(f"Query string (sin firma): {query_string}")
        logger.debug(f"Query string (firmado): {query_string_signed}") # Cuidado al loguear firmas si la seguridad es crítica
        logger.debug(f"Cabeceras: {headers}") # Cuidado al loguear API Keys

        response = requests.get(url, headers=headers, timeout=20) # Aumentado timeout a 20s
        logger.info(f"Respuesta recibida para {merchant_no}. Status: {response.status_code}")
        logger.debug(f"Respuesta RAW para {merchant_no}: {response.text}") # Loguea el texto crudo

        # Verificar si el status code es de éxito antes de intentar parsear JSON
        if response.status_code != 200:
             logger.error(f"Error en la petición para {merchant_no}. Status Code: {response.status_code}. Respuesta: {response.text}")
             return {"error": f"Error HTTP {response.status_code}", "details": response.text}

        # Intentar parsear JSON
        try:
            data = response.json()
            logger.debug(f"Datos JSON recibidos para {merchant_no}: {json.dumps(data, indent=2)}") # Loguea el JSON formateado
        except json.JSONDecodeError as json_err:
            logger.exception(f"Error al decodificar JSON para {merchant_no}. Respuesta: {response.text}")
            return {"error": "Respuesta inválida (no es JSON)", "details": response.text}


        # Verificar el campo 'success' de la respuesta de Binance
        if not data.get("success", False):
            error_msg = data.get("message", "Sin mensaje de error específico")
            error_code = data.get("code", "N/A")
            logger.error(f"Error en respuesta de Binance API para {merchant_no}. Success=False. Code: {error_code}, Message: {error_msg}. Data: {data}")
            return {"error": f"Error API Binance: {error_msg} (Code: {error_code})"}

        # Extraer datos si todo fue bien
        if "data" not in data or not data["data"] or "merchant" not in data["data"] or not data["data"]["merchant"]:
             logger.error(f"Formato de respuesta inesperado para {merchant_no}. Falta 'data' o 'merchant'. Data: {data}")
             return {"error": "Formato de respuesta inesperado", "details": data}

        merchant = data["data"]["merchant"]
        stats = merchant.get("userStatsResp") # Usar .get() para seguridad

        if not stats:
            logger.error(f"No se encontraron 'userStatsResp' para {merchant_no}. Merchant data: {merchant}")
            return {"error": "Faltan estadísticas del usuario ('userStatsResp')", "details": merchant}

        detalles = {
            "nick": merchant.get("nickName", "Desconocido"),
            "compras": int(stats.get("completedBuyOrderNumOfLatest30day", 0)),
            "ventas": int(stats.get("completedSellOrderNumOfLatest30day", 0)),
            "btc_compras": float(stats.get("completedBuyOrderTotalBtcAmount", 0.0)),
            "btc_ventas": float(stats.get("completedSellOrderTotalBtcAmount", 0.0))
        }
        logger.info(f"Detalles obtenidos con éxito para {merchant_no}: Nick={detalles['nick']}, Compras={detalles['compras']}, Ventas={detalles['ventas']}")
        return detalles

    except requests.exceptions.Timeout:
        logger.exception(f"Timeout al obtener detalles para {merchant_no} desde {url}")
        return {"error": "Timeout en la conexión a Binance"}
    except requests.exceptions.ConnectionError:
        logger.exception(f"Error de conexión al obtener detalles para {merchant_no} desde {url}")
        return {"error": "Error de conexión (posiblemente sin internet o DNS)"}
    except requests.exceptions.RequestException as req_err:
        logger.exception(f"Error de Requests al obtener detalles para {merchant_no}: {req_err}")
        return {"error": f"Error de red/HTTP: {str(req_err)}"}
    except Exception as e:
        # Captura cualquier otro error inesperado
        logger.exception(f"Error inesperado al obtener detalles para {merchant_no}: {e}")
        return {"error": f"Error inesperado en obtener_detalles_usuario: {str(e)}"}

def obtener_precio_btc_usdt():
    logger.debug("Intentando obtener precio BTC/USDT...")
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Respuesta de precio BTC/USDT. Status: {response.status_code}")
        logger.debug(f"Respuesta RAW de precio: {response.text}")
        response.raise_for_status() # Lanza excepción para errores HTTP (4xx, 5xx)
        data = response.json()
        precio = float(data["price"])
        logger.info(f"Precio BTC/USDT obtenido: {precio}")
        return precio
    except requests.exceptions.Timeout:
        logger.exception(f"Timeout al obtener precio BTC/USDT desde {url}")
        return 0.0
    except requests.exceptions.ConnectionError:
        logger.exception(f"Error de conexión al obtener precio BTC/USDT desde {url}")
        return 0.0
    except requests.exceptions.RequestException as req_err:
        logger.exception(f"Error de Requests al obtener precio BTC/USDT: {req_err}")
        return 0.0
    except (KeyError, ValueError, json.JSONDecodeError) as parse_err:
         logger.exception(f"Error al parsear la respuesta de precio BTC/USDT: {parse_err}. Respuesta: {response.text if 'response' in locals() else 'N/A'}")
         return 0.0
    except Exception as e:
        logger.exception(f"Error inesperado al obtener precio BTC/USDT: {e}")
        return 0.0

def actualizar_datos():
    global estado_global, precio_btc_actual
    logger.info("Iniciando bucle de actualización de datos...")
    while True:
        logger.info("----- Inicio de ciclo de actualización -----")
        precio_btc_actual = obtener_precio_btc_usdt()
        if precio_btc_actual == 0.0:
            logger.warning("No se pudo obtener el precio de BTC/USDT en este ciclo.")
        else:
             logger.info(f"Precio BTC/USDT actual: {precio_btc_actual}")

        processed_merchants = 0
        for merchant in MERCHANTS:
            logger.debug(f"Procesando merchant: {merchant}")
            detalles = obtener_detalles_usuario(merchant)

            if "error" in detalles:
                logger.error(f"Error al obtener detalles para {merchant}: {detalles['error']}. Detalles: {detalles.get('details', 'N/A')}")
                # Podrías querer reintentar o simplemente saltar este merchant en este ciclo
                time.sleep(1) # Pequeña pausa si hay error para no saturar
                continue # Pasa al siguiente merchant

            processed_merchants += 1
            logger.debug(f"Detalles recibidos para {merchant}: {detalles}")

            # Inicializar estado si es la primera vez que vemos al merchant
            if merchant not in estado_global:
                logger.info(f"Inicializando estado para nuevo merchant: {merchant} ({detalles['nick']})")
                estado_global[merchant] = {
                    "nick": detalles["nick"],
                    "compras_base": detalles["compras"],
                    "ventas_base": detalles["ventas"],
                    "btc_compra_base": detalles["btc_compras"],
                    "btc_venta_base": detalles["btc_ventas"],
                    "compras_total": 0, # Inicia en 0 relativo a la base
                    "ventas_total": 0, # Inicia en 0 relativo a la base
                    "hora_ultima_compra": "--:--",
                    "hora_ultima_venta": "--:--",
                    "btc_ultima_compra": 0.0,
                    "btc_ultima_venta": 0.0,
                    "usdt_acumulado_compra": 0.0,
                    "usdt_acumulado_venta": 0.0,
                    "timestamp_last_update": datetime.now().isoformat()
                }
                logger.debug(f"Estado inicial para {merchant}: {estado_global[merchant]}")

            # Procesar cambios
            estado = estado_global[merchant]
            comp_act = detalles["compras"]
            vent_act = detalles["ventas"]
            btc_comp_act = detalles["btc_compras"]
            btc_vent_act = detalles["btc_ventas"]
            timestamp_actual = datetime.now()

            logger.debug(f"{merchant} ({estado['nick']}): Compras API={comp_act}, Base={estado['compras_base']}, Total Prev={estado['compras_total']}")
            logger.debug(f"{merchant} ({estado['nick']}): Ventas API={vent_act}, Base={estado['ventas_base']}, Total Prev={estado['ventas_total']}")
            logger.debug(f"{merchant} ({estado['nick']}): BTC Compra API={btc_comp_act}, Base={estado['btc_compra_base']}")
            logger.debug(f"{merchant} ({estado['nick']}): BTC Venta API={btc_vent_act}, Base={estado['btc_venta_base']}")

            # --- Lógica de Compras ---
            # Comparamos el número actual de compras de la API con el número base que guardamos la primera vez
            # Sumamos el total acumulado que ya habíamos detectado desde que inició la app.
            if comp_act >= estado["compras_base"]:
                nuevas_compras_detectadas = comp_act - estado["compras_base"]
                if nuevas_compras_detectadas > estado["compras_total"]:
                    # ¡Se detectaron nuevas compras desde la última vez que revisamos!
                    num_nuevas = nuevas_compras_detectadas - estado["compras_total"]
                    delta_btc = round(btc_comp_act - estado["btc_compra_base"], 8) # Usar más decimales para BTC
                    delta_usdt = round(delta_btc * precio_btc_actual, 2) if precio_btc_actual else 0.0

                    logger.info(f"¡NUEVA COMPRA DETECTADA para {merchant} ({estado['nick']})!")
                    logger.info(f"  - Cantidad: {num_nuevas} (Total detectado: {nuevas_compras_detectadas})")
                    logger.info(f"  - Delta BTC: {delta_btc} (BTC API: {btc_comp_act}, BTC Base: {estado['btc_compra_base']})")
                    logger.info(f"  - Delta USDT (aprox): {delta_usdt} (Precio BTC: {precio_btc_actual})")

                    estado["compras_total"] = nuevas_compras_detectadas # Actualiza el total relativo a la base
                    estado["hora_ultima_compra"] = timestamp_actual.strftime("%H:%M")
                    estado["btc_ultima_compra"] = delta_btc # Guarda el delta de ESTA actualización
                    estado["btc_compra_base"] = btc_comp_act # ¡Actualiza la base BTC para la próxima comparación!
                    estado["usdt_acumulado_compra"] += delta_usdt # Acumula el valor USDT
                elif nuevas_compras_detectadas < estado["compras_total"]:
                     logger.warning(f"Número de compras totales ({nuevas_compras_detectadas}) menor al acumulado previo ({estado['compras_total']}) para {merchant}. ¿Posible reseteo de stats en Binance o error?")
                     # Podrías resetear el estado aquí o investigar
            else:
                logger.warning(f"Número de compras API ({comp_act}) menor a la base inicial ({estado['compras_base']}) para {merchant}. ¿Posible reseteo?")


            # --- Lógica de Ventas ---
            # Similar a las compras
            if vent_act >= estado["ventas_base"]:
                nuevas_ventas_detectadas = vent_act - estado["ventas_base"]
                if nuevas_ventas_detectadas > estado["ventas_total"]:
                    num_nuevas = nuevas_ventas_detectadas - estado["ventas_total"]
                    delta_btc = round(btc_vent_act - estado["btc_venta_base"], 8)
                    delta_usdt = round(delta_btc * precio_btc_actual, 2) if precio_btc_actual else 0.0

                    logger.info(f"¡NUEVA VENTA DETECTADA para {merchant} ({estado['nick']})!")
                    logger.info(f"  - Cantidad: {num_nuevas} (Total detectado: {nuevas_ventas_detectadas})")
                    logger.info(f"  - Delta BTC: {delta_btc} (BTC API: {btc_vent_act}, BTC Base: {estado['btc_venta_base']})")
                    logger.info(f"  - Delta USDT (aprox): {delta_usdt} (Precio BTC: {precio_btc_actual})")

                    estado["ventas_total"] = nuevas_ventas_detectadas
                    estado["hora_ultima_venta"] = timestamp_actual.strftime("%H:%M")
                    estado["btc_ultima_venta"] = delta_btc
                    estado["btc_venta_base"] = btc_vent_act # ¡Actualiza la base BTC!
                    estado["usdt_acumulado_venta"] += delta_usdt
                elif nuevas_ventas_detectadas < estado["ventas_total"]:
                     logger.warning(f"Número de ventas totales ({nuevas_ventas_detectadas}) menor al acumulado previo ({estado['ventas_total']}) para {merchant}. ¿Posible reseteo de stats en Binance o error?")
            else:
                logger.warning(f"Número de ventas API ({vent_act}) menor a la base inicial ({estado['ventas_base']}) para {merchant}. ¿Posible reseteo?")

            # Actualizar timestamp de última revisión exitosa para este merchant
            estado["timestamp_last_update"] = timestamp_actual.isoformat()

            # Pequeña pausa entre merchants para no exceder límites de API
            time.sleep(0.5) # 500 ms entre cada merchant

        logger.info(f"----- Fin de ciclo de actualización. Merchants procesados con éxito: {processed_merchants}/{len(MERCHANTS)} -----")
        # Espera antes del próximo ciclo completo
        sleep_time = 30
        logger.debug(f"Esperando {sleep_time} segundos para el próximo ciclo.")
        time.sleep(sleep_time)


@app.route('/')
def index():
    logger.info(f"Solicitud recibida para la ruta '/' desde {request.remote_addr}")
    return render_template('index.html')

@app.route('/api/datos')
def get_datos():
    logger.info(f"Solicitud recibida para la ruta '/api/datos' desde {request.remote_addr}")
    # Crear una copia para evitar problemas de concurrencia mientras se itera y actualiza
    estado_actual = estado_global.copy()
    datos_respuesta = {
        'estado': estado_actual,
        'precio_btc': precio_btc_actual,
        'hora_actual': datetime.now().strftime("%H:%M"),
        'fecha_actual': datetime.now().strftime("%d %B")
    }
    logger.debug(f"Enviando datos a /api/datos: {json.dumps(datos_respuesta, indent=2, default=str)}") # default=str para manejar datetime si estuviera
    return jsonify(datos_respuesta)

if __name__ == '__main__':
    logger.info("Creando e iniciando el hilo de actualización de datos...")
    # Iniciar el hilo que actualiza los datos en segundo plano
    # daemon=True significa que el hilo terminará si el programa principal termina
    thread = Thread(target=actualizar_datos, daemon=True, name="UpdateThread")
    thread.start()
    logger.info("Hilo de actualización iniciado.")

    # Obtener puerto de variable de entorno o usar 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor Flask en host 0.0.0.0 puerto {port}")

    # Ejecutar la aplicación Flask
    # debug=False es importante para producción. El logging ya está configurado.
    # usar 'waitress' o 'gunicorn' es mejor para producción que el server de desarrollo de Flask.
    app.run(host='0.0.0.0', port=port, debug=False)
