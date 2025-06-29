# mi-portafolio-bots/edubot/channels/instagram/instagram_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de Meta

# --- Configuración para la importación del core del bot ---
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
    sys.exit(1)

instagram_app = Flask(__name__)

# --- CONFIGURACIÓN DE INSTAGRAM/FACEBOOK MESSENGER API (PLACEHOLDERS) ---
# Reemplaza estos con tus credenciales REALES de Facebook Developers para EduBot
EDUBOT_PAGE_ACCESS_TOKEN = os.environ.get("EDUBOT_PAGE_ACCESS_TOKEN", "YOUR_EDUBOT_PAGE_ACCESS_TOKEN")
EDUBOT_VERIFY_TOKEN = os.environ.get("EDUBOT_INSTAGRAM_VERIFY_TOKEN", "YOUR_EDUBOT_INSTAGRAM_VERIFY_TOKEN")
META_MESSENGER_API_URL = "https://graph.facebook.com/v19.0/me/messages"

# --- Webhook de Verificación de Meta (para Instagram/Messenger) ---
@instagram_app.route('/webhook', methods=['GET'])
def instagram_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == EDUBOT_VERIFY_TOKEN:
            print("EduBot Instagram/Messenger Webhook Verified!")
            return challenge, 200
        else:
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    return "OK", 200

# --- Webhook Principal de Mensajes de Instagram/Messenger ---
@instagram_app.route('/webhook', methods=['POST'])
def instagram_message_webhook():
    data = request.get_json()
    print(f"Received EduBot Instagram/Messenger data: {data}")

    try:
        if 'object' in data and data['object'] == 'page':
            for entry in data['entry']:
                for messaging_event in entry['messaging']:
                    sender_id = messaging_event['sender']['id'] # ID del usuario (psid de Messenger)

                    # Manejar mensajes de texto
                    if 'message' in messaging_event and 'text' in messaging_event['message']:
                        user_message = messaging_event['message']['text']
                        print(f"EduBot Instagram/Messenger message from {sender_id}: {user_message}")

                        # Cargar el contexto del usuario (desde una base de datos real en prod)
                        current_context = conversation_contexts.get(sender_id, {
                            "step": "welcome",
                            "last_queried_course_code": None,
                            "contact_info": {}
                        })
                        
                        # Procesar el mensaje con la lógica central del bot de EduBot
                        bot_response_result = handle_edubot_message(user_message, current_context)
                        bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                        updated_context = bot_response_result.get('context', current_context)

                        # Guardar el contexto actualizado (en una base de datos real en prod)
                        conversation_contexts[sender_id] = updated_context
                        
                        # Enviar la respuesta a la API de Meta
                        send_meta_message(sender_id, bot_text_response, EDUBOT_PAGE_ACCESS_TOKEN)
                        
                        return jsonify({"status": "success", "message": "Message processed"}), 200
                    
                    # Manejar Postbacks (clics en botones de plantillas)
                    elif 'postback' in messaging_event:
                        payload = messaging_event['postback']['payload']
                        print(f"EduBot Instagram/Messenger Postback from {sender_id}: {payload}")

                        # Usamos el payload del postback como si fuera un mensaje del usuario
                        current_context = conversation_contexts.get(sender_id, {
                            "step": "welcome",
                            "last_queried_course_code": None,
                            "contact_info": {}
                        })
                        
                        bot_response_result = handle_edubot_message(payload, current_context)
                        bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                        updated_context = bot_response_result.get('context', current_context)

                        conversation_contexts[sender_id] = updated_context
                        
                        send_meta_message(sender_id, bot_text_response, EDUBOT_PAGE_ACCESS_TOKEN)
                        
                        return jsonify({"status": "success", "message": "Postback processed"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a relevant message type or invalid structure"}), 200

    except Exception as e:
        print(f"Error processing EduBot Instagram/Messenger webhook: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

def send_meta_message(recipient_id, text_message, access_token):
    """Envía un mensaje de texto usando la API de Meta Messenger."""
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "access_token": access_token
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text_message}
    }
    try:
        response = requests.post(META_MESSENGER_API_URL, headers=headers, params=params, json=payload)
        response.raise_for_status()
        print(f"EduBot Meta message sent successfully to {recipient_id}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending EduBot Meta message to {recipient_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5007)) # Puerto diferente para EduBot Instagram (ej. 5007)
    instagram_app.run(host='0.0.0.0', port=port, debug=True)