# mi-portafolio-bots/healthbot/channels/instagram/instagram_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar y recibir de las APIs
import json     # Para el manejo de JSON
from dotenv import load_dotenv # Para cargar variables de entorno

# Cargar variables de entorno desde el archivo .env
load_dotenv()

healthbot_instagram_connector_app = Flask(__name__)

# --- CONFIGURACIÓN DE INSTAGRAM / META GRAPH API ---
# Necesitarás un Access Token de la página de Facebook conectada a tu Instagram Business/Creator
HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN = os.environ.get("HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN", "YOUR_HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN")
# Este es el Token de Verificación que configuras en la sección de Webhooks de tu App de Meta para Instagram
HEALTHBOT_INSTAGRAM_VERIFY_TOKEN = os.environ.get("HEALTHBOT_INSTAGRAM_VERIFY_TOKEN", "YOUR_HEALTHBOT_INSTAGRAM_VERIFY_TOKEN")

# Validaciones básicas de configuración
if HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN == "YOUR_HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN":
    print("ADVERTENCIA: HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN no configurado en .env o usando valor por defecto.", file=sys.stderr)
if HEALTHBOT_INSTAGRAM_VERIFY_TOKEN == "YOUR_HEALTHBOT_INSTAGRAM_VERIFY_TOKEN":
    print("ADVERTENCIA: HEALTHBOT_INSTAGRAM_VERIFY_TOKEN no configurado en .env o usando valor por defecto.", file=sys.stderr)

# URL Base para la API de mensajes de Instagram (parte de Meta Graph API)
# Asegúrate de usar la versión más reciente de la API (v19.0 es actual a la fecha)
INSTAGRAM_API_URL = "https://graph.facebook.com/v19.0/me/messages"

# --- URL de tu backend HealthBot (app.py) ---
# Esta es la URL donde tu app.py está escuchando las solicitudes del bot.
HEALTHBOT_API_URL = "http://localhost:5010/api/healthbot_chat"

# Almacenamiento de contexto de conversación (simulado en memoria)
# En producción, esto debería ser una base de datos persistente.
conversation_contexts_instagram = {}

# --- Webhook de Verificación de Meta (para Instagram) ---
@healthbot_instagram_connector_app.route('/webhook', methods=['GET'])
def instagram_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == HEALTHBOT_INSTAGRAM_VERIFY_TOKEN:
            print("HealthBot Instagram Webhook Verified!")
            return challenge, 200
        else:
            print("Verification failed: Token mismatch")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    print("Verification failed: Missing mode or token")
    return "OK", 200 # Responde OK incluso si faltan parámetros para evitar errores de conexión inicial

# --- Webhook Principal de Mensajes de Instagram ---
@healthbot_instagram_connector_app.route('/webhook', methods=['POST'])
def instagram_message_webhook():
    data = request.get_json()
    print(f"Received HealthBot Instagram data: {json.dumps(data, indent=2)}")

    try:
        if 'entry' in data and data['entry']:
            for entry in data['entry']:
                if 'messaging' in entry and entry['messaging']:
                    for message_event in entry['messaging']:
                        sender_id = message_event['sender']['id'] # ID del usuario de Instagram

                        user_message_text = None
                        
                        # Manejo de mensajes de texto
                        if 'message' in message_event and 'text' in message_event['message']:
                            user_message_text = message_event['message']['text']
                        # Manejo de "Quick Replies" (botones de respuesta rápida)
                        elif 'postback' in message_event: # También se pueden usar para Quick Replies complejas o botones persistentes
                            user_message_text = message_event['postback'].get('payload', message_event['postback'].get('title'))
                        elif 'message' in message_event and 'quick_reply' in message_event['message']:
                            user_message_text = message_event['message']['quick_reply'].get('payload', message_event['message']['text'])
                            # El 'payload' es lo que enviaste al crear el quick_reply,
                            # el 'text' es lo que el usuario ve. Si envías solo texto en el payload, ambos son iguales.
                        
                        if user_message_text:
                            print(f"HealthBot Instagram message from {sender_id}: {user_message_text}")

                            # Obtener el contexto actual del usuario
                            current_context = conversation_contexts_instagram.get(sender_id, {
                                "step": "welcome",
                                "selected_service_code": None,
                                "selected_doctor": None,
                                "booking_details": {},
                                "patient_info": {
                                    "prepaga": None,
                                    "name": None,
                                    "phone": None,
                                    "email": None
                                },
                                "booking_id_for_action": None,
                                "current_action": None
                            })
                            
                            # Enviar el mensaje y el contexto a tu backend HealthBot
                            healthbot_api_payload = {
                                'message': user_message_text,
                                'context': current_context,
                                'user_id': str(sender_id) # Usamos el ID del remitente de Instagram como user_id
                            }
                            
                            healthbot_response = requests.post(HEALTHBOT_API_URL, json=healthbot_api_payload, timeout=30)
                            healthbot_response.raise_for_status() # Lanza excepción para errores HTTP
                            
                            healthbot_result = healthbot_response.json()
                            bot_text_response = healthbot_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                            updated_context = healthbot_result.get('context', current_context)
                            response_data = healthbot_result.get('data', None) # Datos adicionales como botones

                            # Guardar el contexto actualizado
                            conversation_contexts_instagram[sender_id] = updated_context
                            
                            # Enviar la respuesta a Instagram, incluyendo Quick Replies si existen
                            send_instagram_message(sender_id, bot_text_response, response_data)
                            
                            return jsonify({"status": "success", "message": "Message processed"}), 200
                        else:
                            print(f"Received unsupported message type or no text from Instagram: {message_event}", file=sys.stderr)
                            # Puedes decidir ignorar o enviar un mensaje de "no soportado"
                            return jsonify({"status": "ignored", "message": "Unsupported message type"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a relevant Instagram update or invalid structure"}), 200

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con HealthBot API: {e}", file=sys.stderr)
        # Intentar responder al usuario si la conexión al backend falla
        if 'entry' in data and data['entry'] and 'messaging' in data['entry'][0] and data['entry'][0]['messaging']:
            sender_id_on_error = data['entry'][0]['messaging'][0]['sender']['id']
            send_instagram_message(sender_id_on_error, "Lo siento, hubo un problema técnico al comunicarme con el asistente. Por favor, inténtalo más tarde.", None)
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        print(f"Error processing HealthBot Instagram webhook: {e}", file=sys.stderr)
        if 'entry' in data and data['entry'] and 'messaging' in data['entry'][0] and data['entry'][0]['messaging']:
            sender_id_on_error = data['entry'][0]['messaging'][0]['sender']['id']
            send_instagram_message(sender_id_on_error, "Lo siento, hubo un error inesperado. Por favor, inténtalo de nuevo.", None)
        return jsonify({"status": "error", "message": str(e)}), 500

def send_instagram_message(recipient_id, text_message, response_data=None):
    """
    Envía un mensaje a Instagram.
    Adapta los 'action_buttons' del bot a los 'Quick Replies' de Instagram.
    """
    if not HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN:
        print("Error: HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN no configurado para enviar mensaje.", file=sys.stderr)
        return {"error": "Missing Instagram API credentials"}

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text_message}
    }

    # Si hay botones de acción desde el bot, los convertimos a "Quick Replies" de Instagram
    if response_data and response_data.get('type') == 'action_buttons' and response_data.get('buttons'):
        quick_replies = []
        for btn in response_data['buttons']:
            quick_replies.append({
                "content_type": "text",
                "title": btn['text'], # El texto visible del botón
                "payload": btn.get('action', btn['text']) # Lo que se enviará de vuelta al bot cuando se toque el botón
            })
        payload["message"]["quick_replies"] = quick_replies
        
    # Parámetros de la URL (incluyendo el access token)
    params = {"access_token": HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN}

    try:
        response = requests.post(INSTAGRAM_API_URL, headers=headers, json=payload, params=params)
        response.raise_for_status()
        print(f"HealthBot Instagram message sent successfully to {recipient_id}: {text_message}. Payload: {json.dumps(payload)}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending HealthBot Instagram message to {recipient_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    # Puerto diferente para Instagram (ej. 5009)
    port = int(os.environ.get('INSTAGRAM_CONNECTOR_PORT', 5009)) 
    print(f"Starting HealthBot Instagram Connector on port {port}...")
    if HEALTHBOT_INSTAGRAM_VERIFY_TOKEN == "YOUR_HEALTHBOT_INSTAGRAM_VERIFY_TOKEN":
        print("ADVERTENCIA: Usando token de verificación por defecto para Instagram. Cámbiarlo en .env!", file=sys.stderr)
    if not HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN:
         print("ADVERTENCIA: HEALTHBOT_INSTAGRAM_PAGE_ACCESS_TOKEN no está configurado. No se podrán enviar respuestas.", file=sys.stderr)

    healthbot_instagram_connector_app.run(host='0.0.0.0', port=port, debug=True)