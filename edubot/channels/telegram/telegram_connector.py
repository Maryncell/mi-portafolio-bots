# mi-portafolio-bots/edubot/channels/telegram/telegram_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de Telegram

# --- Configuración para la importación del core del bot ---
# Calcula la ruta de la raíz del proyecto dinámicamente.
# Esto asume que este archivo está en mi-portafolio-bots/edubot/channels/telegram/
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

telegram_app = Flask(__name__)

# --- CONFIGURACIÓN DE TELEGRAM API (PLACEHOLDERS) ---
# Reemplaza esto con el TOKEN REAL de tu BOT DE TELEGRAM para EduBot
TELEGRAM_BOT_TOKEN = os.environ.get("EDUBOT_TELEGRAM_BOT_TOKEN", "YOUR_EDUBOT_TELEGRAM_BOT_TOKEN") 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"

# --- Webhook Principal de Telegram ---
@telegram_app.route('/webhook', methods=['POST'])
def telegram_message_webhook():
    data = request.get_json()
    print(f"Received Telegram data: {data}")

    try:
        chat_id = None
        user_message = None
        
        # Manejar mensajes de texto
        if 'message' in data and 'text' in data['message']:
            chat_id = data['message']['chat']['id']
            user_message = data['message']['text']
        # Manejar callbacks de botones (si usas botones inline en Telegram)
        elif 'callback_query' in data:
            chat_id = data['callback_query']['message']['chat']['id']
            user_message = data['callback_query']['data'] # El 'data' del botón es el 'mensaje'
            # Opcional: Responder al callback para quitar el "cargando" del botón
            requests.post(TELEGRAM_API_URL + "answerCallbackQuery", json={"callback_query_id": data['callback_query']['id']})

        if chat_id and user_message:
            # Cargar el contexto del usuario. En una app real, esto sería de una DB.
            current_context = conversation_contexts.get(chat_id, {
                "step": "welcome",
                "last_queried_course_code": None,
                "contact_info": {}
            })
            
            print(f"EduBot Telegram message from {chat_id}: {user_message}")

            # Procesar el mensaje con la lógica central del bot de EduBot
            bot_response_result = handle_edubot_message(user_message, current_context)
            bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
            updated_context = bot_response_result.get('context', current_context)

            # Guardar el contexto actualizado
            conversation_contexts[chat_id] = updated_context
            
            # Enviar la respuesta a la API de Telegram
            send_telegram_message(chat_id, bot_text_response)
            
            return jsonify({"status": "success", "message": "Message processed"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a recognized Telegram update"}), 200

    except Exception as e:
        print(f"Error processing EduBot Telegram webhook: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": str(e)}), 500

def send_telegram_message(chat_id, text_message):
    """Envía un mensaje de texto a Telegram usando la API de Bot."""
    url = TELEGRAM_API_URL + "sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "parse_mode": "Markdown" # Telegram soporta negritas con Markdown (**)
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"EduBot Telegram message sent successfully to {chat_id}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending EduBot Telegram message to {chat_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    # Este conector se ejecutaría como una app Flask independiente.
    # Necesitarías exponerlo públicamente (ej. con ngrok) para que Telegram lo alcance.
    port = int(os.environ.get('PORT', 5006)) # Puerto diferente para EduBot Telegram (ej. 5006)
    telegram_app.run(host='0.0.0.0', port=port, debug=True)