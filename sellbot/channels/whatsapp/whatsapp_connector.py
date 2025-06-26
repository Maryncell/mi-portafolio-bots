# channels/whatsapp/whatsapp_connector.py

from flask import Flask, request, jsonify
import requests
import os

# Inicializa la aplicación Flask para el conector de WhatsApp.
app = Flask(__name__)

# URL del cerebro de Sellbot (tu app.py). En un despliegue real, sería una URL pública.
# Asegúrate de que esta URL sea correcta si tu core se ejecuta en un servidor diferente.
SELLBOT_CORE_URL = os.getenv("SELLBOT_CORE_URL", "http://localhost:5000/api/sellbot_chat")

# Token de verificación para el webhook de WhatsApp (necesario para la configuración inicial)
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "YOUR_RANDOM_VERIFY_TOKEN")
# Token de acceso de la API de WhatsApp Business
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "YOUR_WHATSAPP_API_TOKEN")
# ID del número de teléfono de WhatsApp Business
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "YOUR_PHONE_NUMBER_ID")

# Endpoint para la verificación del webhook de WhatsApp (GET request)
@app.route('/whatsapp-webhook', methods=['GET'])
def whatsapp_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("Webhook verificado con éxito para WhatsApp!")
            return challenge, 200
        else:
            print("Error de verificación del Webhook de WhatsApp.")
            return 'Verification token mismatch', 403
    return 'Missing parameters', 400

# Endpoint para recibir mensajes de WhatsApp (POST request)
@app.route('/whatsapp-webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.json
    print(f"Datos recibidos de WhatsApp: {data}")

    # Procesar los mensajes entrantes de WhatsApp
    # La estructura de los datos de WhatsApp puede variar según el proveedor (Meta, Twilio, etc.)
    # Este es un ejemplo básico para la API de Meta/WhatsApp Business
    try:
        entry = data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        messages = value.get('messages')

        if messages:
            message = messages[0]
            if message['type'] == 'text':
                user_id = message['from'] # Número de teléfono del remitente
                user_message_text = message['text']['body']
                print(f"Mensaje de WhatsApp de {user_id}: {user_message_text}")

                # 1. Enviar el mensaje al núcleo de Sellbot
                sellbot_response = requests.post(SELLBOT_CORE_URL, json={
                    'message': user_message_text,
                    'context': {}, # En un entorno real, se almacenaría el contexto por user_id
                    'channel': 'whatsapp',
                    'user_id': user_id # Pasar user_id al core para rastreo
                }).json()
                
                response_text = sellbot_response.get('response', 'Lo siento, hubo un error en el bot.')
                response_data = sellbot_response.get('data')

                # 2. Formatear y enviar la respuesta de vuelta a WhatsApp
                whatsapp_api_url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
                    "Content-Type": "application/json"
                }

                # Ejemplo simplificado de formateo para WhatsApp
                whatsapp_message_payload = {
                    "messaging_product": "whatsapp",
                    "to": user_id,
                    "type": "text",
                    "text": {"body": response_text}
                }

                # Si hay datos de producto, podríamos enviar un mensaje interactivo con producto/botones
                if response_data and response_data.get('type') in ['product_card', 'product_card_buy_options']:
                    product = response_data
                    # Esto requiere que tengas un catálogo de productos configurado en WhatsApp Business.
                    whatsapp_message_payload = {
                        "messaging_product": "whatsapp",
                        "to": user_id,
                        "type": "interactive",
                        "interactive": {
                            "type": "product", # Para tarjetas de producto
                            "body": {"text": response_text},
                            "action": {
                                "catalog_id": "YOUR_CATALOG_ID", # Requerido para productos de WhatsApp Business.
                                "product_retailer_id": product['code']
                            }
                        }
                    }
                    # Alternativamente, para botones personalizados (si no usas el catálogo de WhatsApp):
                    # whatsapp_message_payload = {
                    #     "messaging_product": "whatsapp",
                    #     "to": user_id,
                    #     "type": "interactive",
                    #     "interactive": {
                    #         "type": "button",
                    #         "body": {"text": response_text},
                    #         "action": {
                    #             "buttons": [
                    #                 {"type": "reply", "reply": {"id": "buy_" + product['code'], "title": "Comprar"}},
                    #                 {"type": "reply", "reply": {"id": "details_" + product['code'], "title": "Más info"}}
                    #             ]
                    #         }
                    #     }
                    # }

                # Enviar la respuesta de WhatsApp
                send_response = requests.post(whatsapp_api_url, headers=headers, json=whatsapp_message_payload)
                print(f"Respuesta de WhatsApp API: {send_response.status_code}, {send_response.json()}")

    except Exception as e:
        print(f"Error al procesar el mensaje de WhatsApp: {e}")
        # Enviar un mensaje de error genérico al usuario de WhatsApp
        # Asegúrate de que user_id esté disponible en caso de error
        if 'user_id' in locals(): # Verifica si user_id fue definido antes del error
            error_api_url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
            error_headers = {
                "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            error_payload = {
                "messaging_product": "whatsapp",
                "to": user_id,
                "type": "text",
                "text": {"body": "Lo siento, un error ha ocurrido en nuestro sistema. Por favor, inténtalo de nuevo más tarde."}
            }
            requests.post(error_api_url, headers=error_headers, json=error_payload)

    return jsonify({"status": "received"}), 200

# Ejecutar el conector de WhatsApp
if __name__ == '__main__':
    # Usar un puerto diferente al del core Sellbot, por ejemplo 5001
    # Para pruebas locales con webhooks, se usaría ngrok o similar para exponer este puerto.
    app.run(debug=True, port=5001)