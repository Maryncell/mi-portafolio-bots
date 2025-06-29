# mi-portafolio-bots/agendabot/channels/whatsapp/whatsapp_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de WhatsApp

# --- Configuración para la importación del core del bot ---
# Asegura que el directorio 'mi-portafolio-bots' (la raíz del proyecto) esté en sys.path
# Esto permite importar 'agendabot.core.app' aunque no haya __init__.py en los directorios intermedios.
# Calcula la ruta de la raíz del proyecto dinámicamente.
# Esto asume que este archivo está en mi-portafolio-bots/agendabot/channels/whatsapp/
current_dir = os.path.dirname(os.path.abspath(__file__))
agendabot_root_dir = os.path.join(current_dir, '..', '..') # Sube dos niveles para llegar a agendabot/
# Ahora sube un nivel más para llegar a mi-portafolio-bots/
project_root_dir = os.path.join(agendabot_root_dir, '..')

if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importa la función principal de lógica del bot desde agendabot.core.app
# Necesitarás asegurarte de que agendabot/core/app.py esté ejecutándose, o que esta importación sea válida
# cuando este conector sea el que se expone.
# En un escenario de producción, podrías tener un "broker" de mensajes o una arquitectura diferente.
# Para esta demo, asumimos que 'agendabot.core.app' es importable o que su lógica es accesible.
try:
    from agendabot.core.app import handle_agendabot_message, conversation_contexts
except ImportError as e:
    print(f"Error al importar handle_agendabot_message: {e}")
    print("Asegúrate de que 'mi-portafolio-bots' está en tu PYTHONPATH o ejecuta desde la raíz del proyecto.")
    sys.exit(1) # Salir si no se puede importar la lógica del bot

whatsapp_app = Flask(__name__)

# --- CONFIGURACIÓN DE WHATSAPP API (PLACEHOLDERS) ---
# Reemplaza estos con tus credenciales reales
WHATSAPP_API_TOKEN = "YOUR_WHATSAPP_API_TOKEN" # Desde Meta Developers / Twilio
WHATSAPP_PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID" # Desde Meta Developers (ID del número)
META_GRAPH_API_URL = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages" # Para Meta Business API

# --- Webhook de Verificación de Meta Business API (si aplica) ---
@whatsapp_app.route('/webhook', methods=['GET'])
def whatsapp_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Reemplaza 'YOUR_VERIFY_TOKEN' con el token de verificación que configuraste en Meta
    VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "YOUR_VERIFY_TOKEN") 

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WhatsApp Webhook Verified!")
            return challenge, 200
        else:
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    return "OK", 200 # Respuesta por defecto si no es una solicitud de verificación

# --- Webhook Principal de Mensajes de WhatsApp ---
@whatsapp_app.route('/webhook', methods=['POST'])
def whatsapp_message_webhook():
    data = request.get_json()
    print(f"Received WhatsApp data: {data}")

    try:
        # Extraer el mensaje y el ID del remitente de la estructura de webhook de Meta
        if 'entry' in data and data['entry']:
            for entry in data['entry']:
                if 'changes' in entry and entry['changes']:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            for message_data in change['value']['messages']:
                                if message_data['type'] == 'text':
                                    user_message = message_data['text']['body']
                                    sender_id = message_data['from'] # Número de teléfono del usuario
                                    
                                    # Cargar el contexto del usuario (desde una base de datos real en prod)
                                    # Para esta demo, si el contexto no existe, se inicializa vacío
                                    current_context = conversation_contexts.get(sender_id, {"step": "welcome", "selected_service_code": None, "booking_details": {}})
                                    
                                    print(f"WhatsApp message from {sender_id}: {user_message}")

                                    # Procesar el mensaje con la lógica central del bot
                                    bot_response_result = handle_agendabot_message(user_message, current_context)
                                    bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
                                    updated_context = bot_response_result.get('context', current_context)

                                    # Guardar el contexto actualizado (en una base de datos real en prod)
                                    conversation_contexts[sender_id] = updated_context
                                    
                                    # Enviar la respuesta a la API de WhatsApp
                                    send_whatsapp_message(sender_id, bot_text_response)
                                    
                                    return jsonify({"status": "success", "message": "Message processed"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a relevant message type or invalid structure"}), 200

    except Exception as e:
        print(f"Error processing WhatsApp webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_whatsapp_message(recipient_phone_number, text_message):
    """Envía un mensaje de texto a WhatsApp usando Meta Business API."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone_number,
        "type": "text",
        "text": {"body": text_message}
    }
    try:
        response = requests.post(META_GRAPH_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Lanza un error si la solicitud no fue exitosa (4xx o 5xx)
        print(f"WhatsApp message sent successfully to {recipient_phone_number}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message to {recipient_phone_number}: {e}")
        if response.status_code:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        return {"error": str(e)}

if __name__ == '__main__':
    # Este conector se ejecutaría como una app Flask independiente.
    # Necesitarías exponerlo públicamente (ej. con ngrok) para que WhatsApp lo alcance.
    port = int(os.environ.get('PORT', 5011)) # Usar un puerto diferente al del app.py principal
    whatsapp_app.run(host='0.0.0.0', port=port, debug=True)