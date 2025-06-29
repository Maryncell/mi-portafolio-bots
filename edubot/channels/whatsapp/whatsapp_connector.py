# mi-portafolio-bots/edubot/channels/whatsapp/whatsapp_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de WhatsApp

# --- Configuración para la importación del core del bot ---
# Calcula la ruta de la raíz del proyecto dinámicamente.
# Esto asume que este archivo está en mi-portafolio-bots/edubot/channels/whatsapp/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.join(current_dir, '..', '..', '..') # Sube tres niveles para llegar a mi-portafolio-bots/

if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importa la función principal de lógica del bot y los contextos de conversación de EduBot.
try:
    from edubot.core.app import handle_edubot_message, conversation_contexts
except ImportError as e:
    print(f"Error al importar handle_edubot_message o conversation_contexts: {e}")
    print("Asegúrate de que la ruta de importación es correcta y que 'mi-portafolio-bots' está accesible.")
    sys.exit(1) # Salir si no se puede importar la lógica del bot

whatsapp_app = Flask(__name__)

# --- CONFIGURACIÓN DE WHATSAPP BUSINESS PLATFORM API (PLACEHOLDERS) ---
# Reemplaza estos con tus credenciales REALES de Meta para EduBot
# Obtén tu token de acceso permanente desde tu aplicación de Meta Developers
EDUBOT_WA_ACCESS_TOKEN = os.environ.get("EDUBOT_WA_ACCESS_TOKEN", "YOUR_EDUBOT_WHATSAPP_PERMANENT_ACCESS_TOKEN")
# Este es el Token de Verificación que configuras en la sección de Webhooks de tu App de Meta
EDUBOT_WA_VERIFY_TOKEN = os.environ.get("EDUBOT_WA_VERIFY_TOKEN", "YOUR_EDUBOT_WHATSAPP_VERIFY_TOKEN")
# Este es el ID de tu Número de Teléfono de WhatsApp Business API (no el número en sí)
EDUBOT_WA_PHONE_NUMBER_ID = os.environ.get("EDUBOT_WA_PHONE_NUMBER_ID", "YOUR_EDUBOT_WHATSAPP_PHONE_NUMBER_ID")

# URL Base para la API de WhatsApp Cloud
WHATSAPP_API_URL = f"https://graph.facebook.com/v19.0/{EDUBOT_WA_PHONE_NUMBER_ID}/messages"

# --- Webhook de Verificación de Meta (para WhatsApp) ---
@whatsapp_app.route('/webhook', methods=['GET'])
def whatsapp_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == EDUBOT_WA_VERIFY_TOKEN:
            print("EduBot WhatsApp Webhook Verified!")
            return challenge, 200
        else:
            print("Verification failed: Token mismatch")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    print("Verification failed: Missing mode or token")
    return "OK", 200

# --- Webhook Principal de Mensajes de WhatsApp ---
@whatsapp_app.route('/webhook', methods=['POST'])
def whatsapp_message_webhook():
    data = request.get_json()
    print(f"Received EduBot WhatsApp data: {data}")

    try:
        if 'object' in data and data['object'] == 'whatsapp_business_account':
            for entry in data['entry']:
                for change in entry['changes']:
                    if 'value' in change and 'messages' in change['value']:
                        for message in change['value']['messages']:
                            if message['type'] == 'text':
                                sender_id = message['from'] # Número de teléfono del usuario
                                user_message = message['text']['body']
                                print(f"EduBot WhatsApp message from {sender_id}: {user_message}")

                                # Cargar el contexto del usuario. En una app real, esto sería de una DB.
                                current_context = conversation_contexts.get(sender_id, {
                                    "step": "welcome",
                                    "last_queried_course_code": None,
                                    "contact_info": {}
                                })
                                
                                # Procesar el mensaje con la lógica central del bot de EduBot
                                bot_response_result = handle_edubot_message(user_message, current_context)
                                bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                                updated_context = bot_response_result.get('context', current_context)

                                # Guardar el contexto actualizado
                                conversation_contexts[sender_id] = updated_context
                                
                                # Enviar la respuesta a la API de WhatsApp
                                send_whatsapp_message(sender_id, bot_text_response, EDUBOT_WA_ACCESS_TOKEN)
                                
                                return jsonify({"status": "success", "message": "Message processed"}), 200
                            # Aquí puedes añadir manejo para otros tipos de mensajes si es necesario
                            else:
                                print(f"Received unsupported message type: {message['type']}")
                                # Opcional: Enviar un mensaje indicando que el tipo de mensaje no es soportado
                                # send_whatsapp_message(message['from'], "Lo siento, solo puedo procesar mensajes de texto en este momento.", EDUBOT_WA_ACCESS_TOKEN)
        
        return jsonify({"status": "ignored", "message": "Not a relevant message type or invalid structure"}), 200

    except Exception as e:
        print(f"Error processing EduBot WhatsApp webhook: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

def send_whatsapp_message(recipient_id, text_message, access_token):
    """Envía un mensaje de texto a WhatsApp usando la API de Cloud."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": text_message}
    }
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        print(f"EduBot WhatsApp message sent successfully to {recipient_id}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending EduBot WhatsApp message to {recipient_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5008)) # Puerto diferente para EduBot WhatsApp (ej. 5008)
    whatsapp_app.run(host='0.0.0.0', port=port, debug=True)