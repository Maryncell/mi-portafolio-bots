# mi-portafolio-bots/healthbot/channels/whatsapp/whatsapp_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de WhatsApp
import json # Para pretty print del JSON de entrada
from dotenv import load_dotenv # Para cargar variables de entorno desde .env

# Cargar variables de entorno
load_dotenv()

healthbot_whatsapp_connector_app = Flask(__name__)

# --- CONFIGURACIÓN DE WHATSAPP BUSINESS PLATFORM API (PLACEHOLDERS) ---
# Obtén tu token de acceso permanente desde tu aplicación de Meta Developers
HEALTHBOT_WA_ACCESS_TOKEN = os.environ.get("HEALTHBOT_WA_ACCESS_TOKEN", "YOUR_HEALTHBOT_WHATSAPP_PERMANENT_ACCESS_TOKEN")
# Este es el Token de Verificación que configuras en la sección de Webhooks de tu App de Meta
HEALTHBOT_WA_VERIFY_TOKEN = os.environ.get("HEALTHBOT_WA_VERIFY_TOKEN", "YOUR_HEALTHBOT_WHATSAPP_VERIFY_TOKEN")
# Este es el ID de tu Número de Teléfono de WhatsApp Business API (no el número en sí)
HEALTHBOT_WA_PHONE_NUMBER_ID = os.environ.get("HEALTHBOT_WA_PHONE_NUMBER_ID", "YOUR_HEALTHBOT_WHATSAPP_PHONE_NUMBER_ID")

# Validaciones básicas
if HEALTHBOT_WA_ACCESS_TOKEN == "YOUR_HEALTHBOT_WHATSAPP_PERMANENT_ACCESS_TOKEN":
    print("ADVERTENCIA: HEALTHBOT_WA_ACCESS_TOKEN no configurado en .env o usando valor por defecto.", file=sys.stderr)
if HEALTHBOT_WA_VERIFY_TOKEN == "YOUR_HEALTHBOT_WHATSAPP_VERIFY_TOKEN":
    print("ADVERTENCIA: HEALTHBOT_WA_VERIFY_TOKEN no configurado en .env o usando valor por defecto.", file=sys.stderr)
if HEALTHBOT_WA_PHONE_NUMBER_ID == "YOUR_HEALTHBOT_WHATSAPP_PHONE_NUMBER_ID":
    print("ADVERTENCIA: HEALTHBOT_WA_PHONE_NUMBER_ID no configurado en .env o usando valor por defecto.", file=sys.stderr)


# URL para enviar mensajes de respuesta de WhatsApp (Meta Cloud API)
# Se construye dinámicamente con el PHONE_NUMBER_ID
WHATSAPP_API_URL = f"https://graph.facebook.com/v19.0/{HEALTHBOT_WA_PHONE_NUMBER_ID}/messages"

# --- URL de tu backend HealthBot (app.py) ---
# Asegúrate de que esta URL sea accesible desde donde se ejecuta este conector.
HEALTHBOT_API_URL = "http://localhost:5010/api/healthbot_chat"

# Almacenamiento de contexto de conversación (simulado en memoria)
# Esto simula una base de datos para guardar el contexto de cada conversación por usuario.
conversation_contexts_whatsapp = {}

# --- Webhook de Verificación de Meta (para WhatsApp) ---
@healthbot_whatsapp_connector_app.route('/webhook', methods=['GET'])
def whatsapp_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == HEALTHBOT_WA_VERIFY_TOKEN:
            print("HealthBot WhatsApp Webhook Verified!")
            return challenge, 200
        else:
            print("Verification failed: Token mismatch")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    print("Verification failed: Missing mode or token")
    return "OK", 200 # En caso de que no haya mode o token, devuelve OK para no romper la verificación inicial

# --- Webhook Principal de Mensajes de WhatsApp ---
@healthbot_whatsapp_connector_app.route('/webhook', methods=['POST'])
def whatsapp_message_webhook():
    data = request.get_json()
    print(f"Received HealthBot WhatsApp data: {json.dumps(data, indent=2)}")

    try:
        # La estructura de los mensajes de WhatsApp Cloud API es compleja.
        # Navegamos hasta el mensaje de texto.
        if 'object' in data and data['object'] == 'whatsapp_business_account':
            for entry in data['entry']:
                for change in entry['changes']:
                    if 'value' in change and 'messages' in change['value']:
                        for message_obj in change['value']['messages']:
                            # Obtenemos el ID del remitente (número de teléfono)
                            sender_id = message_obj['from'] 
                            
                            user_message = None
                            # Intentamos extraer el mensaje de texto
                            if message_obj['type'] == 'text':
                                user_message = message_obj['text']['body']
                            elif message_obj['type'] == 'button':
                                # Si es un botón de respuesta rápida
                                user_message = message_obj['button']['text']
                                # Nota: El payload del botón se encuentra en message_obj['button']['payload']
                                # Si quieres usar el payload para el bot, usa esa variable en lugar de text.
                                # Por ahora, usamos el texto visible del botón.
                            # Puedes añadir más tipos de mensajes (interactive, image, etc.)

                            if user_message:
                                print(f"HealthBot WhatsApp message from {sender_id}: {user_message}")

                                # Cargar el contexto del usuario (desde nuestro almacenamiento simulado)
                                current_context = conversation_contexts_whatsapp.get(sender_id, {
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
                                    'message': user_message,
                                    'context': current_context,
                                    'user_id': str(sender_id) # Usamos el número de WhatsApp como user_id
                                }
                                
                                healthbot_response = requests.post(HEALTHBOT_API_URL, json=healthbot_api_payload, timeout=30)
                                healthbot_response.raise_for_status() # Lanza excepción para códigos de estado HTTP erróneos
                                
                                healthbot_result = healthbot_response.json()
                                bot_text_response = healthbot_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                                updated_context = healthbot_result.get('context', current_context)
                                response_data = healthbot_result.get('data', None) # Datos adicionales como botones

                                # Guardar el contexto actualizado
                                conversation_contexts_whatsapp[sender_id] = updated_context
                                
                                # Enviar la respuesta a la API de WhatsApp
                                send_whatsapp_message(sender_id, bot_text_response, response_data)
                                
                                return jsonify({"status": "success", "message": "Message processed"}), 200
                            else:
                                print(f"Received unsupported message type or no text: {message_obj.get('type')}", file=sys.stderr)
                                # Puedes decidir enviar un mensaje de error al usuario o simplemente ignorarlo.
                                # send_whatsapp_message(sender_id, "Lo siento, solo puedo procesar mensajes de texto o respuestas de botones en este momento.", None)
                                return jsonify({"status": "ignored", "message": "Unsupported message type"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a relevant WhatsApp update or invalid structure"}), 200

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con HealthBot API: {e}", file=sys.stderr)
        # Intenta enviar un mensaje de error al usuario de WhatsApp si la conexión falló
        # Es importante que el sender_id esté definido aquí para poder responder.
        if 'entry' in data and data['entry'] and 'changes' in data['entry'][0] and 'value' in data['entry'][0]['changes'][0] and 'messages' in data['entry'][0]['changes'][0]['value'] and data['entry'][0]['changes'][0]['value']['messages']:
            sender_id_on_error = data['entry'][0]['changes'][0]['value']['messages'][0]['from']
            send_whatsapp_message(sender_id_on_error, "Lo siento, hubo un problema técnico al comunicarme con el asistente. Por favor, inténtalo más tarde.", None)
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        print(f"Error processing HealthBot WhatsApp webhook: {e}", file=sys.stderr)
        if 'entry' in data and data['entry'] and 'changes' in data['entry'][0] and 'value' in data['entry'][0]['changes'][0] and 'messages' in data['entry'][0]['changes'][0]['value'] and data['entry'][0]['changes'][0]['value']['messages']:
            sender_id_on_error = data['entry'][0]['changes'][0]['value']['messages'][0]['from']
            send_whatsapp_message(sender_id_on_error, "Lo siento, hubo un error inesperado. Por favor, inténtalo de nuevo.", None)
        return jsonify({"status": "error", "message": str(e)}), 500

def send_whatsapp_message(recipient_id, text_message, response_data=None):
    """
    Envía un mensaje a WhatsApp usando la Meta Cloud API.
    Adapta los 'action_buttons' a los botones interactivos de WhatsApp si es posible.
    """
    if not HEALTHBOT_WA_ACCESS_TOKEN or not HEALTHBOT_WA_PHONE_NUMBER_ID:
        print("Error: Tokens o ID de número de teléfono de WhatsApp no configurados para enviar mensaje.", file=sys.stderr)
        return {"error": "Missing WhatsApp API credentials"}

    headers = {
        "Authorization": f"Bearer {HEALTHBOT_WA_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {
            "body": text_message
        }
    }

    # Adaptar los botones de acción del bot a los botones interactivos de WhatsApp
    if response_data and response_data.get('type') == 'action_buttons' and response_data.get('buttons'):
        # WhatsApp Cloud API permite hasta 3 botones de respuesta rápida (reply buttons)
        # o hasta 10 botones de lista (list message). Para la mayoría de los casos simples,
        # los reply buttons son suficientes.
        buttons = []
        for i, btn in enumerate(response_data['buttons']):
            if i < 3: # Limitar a 3 botones como máximo para reply buttons
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": btn.get('action', btn['text']), # Usar 'action' si existe, sino el 'text'
                        "title": btn['text'] # El texto visible del botón
                    }
                })
        
        if buttons:
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text_message}, # El mensaje principal que acompaña a los botones
                    "action": {"buttons": buttons}
                    # Opcional: "header": {"type": "text", "text": "Título"}
                    # Opcional: "footer": {"text": "Texto pequeño al pie"}
                }
            }

    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        print(f"HealthBot WhatsApp message sent successfully to {recipient_id}. Payload: {json.dumps(payload)}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending HealthBot WhatsApp message to {recipient_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    port = int(os.environ.get('WHATSAPP_CONNECTOR_PORT', 5008)) # Puerto diferente para WhatsApp (ej. 5008)
    print(f"Starting HealthBot WhatsApp Connector on port {port}...")
    healthbot_whatsapp_connector_app.run(host='0.0.0.0', port=port, debug=True)