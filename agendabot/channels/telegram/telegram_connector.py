# mi-portafolio-bots/agendabot/channels/telegram/telegram_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests # Necesario para enviar respuestas a la API de Telegram

# --- Configuración para la importación del core del bot ---
# Asegura que el directorio 'mi-portafolio-bots' (la raíz del proyecto) esté en sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Sube dos niveles para llegar a la carpeta 'agendabot' y luego un nivel más para 'mi-portafolio-bots'
project_root_dir = os.path.join(current_dir, '..', '..', '..') 

if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importa la función principal de lógica del bot desde agendabot.core.app
try:
    # Se importa directamente handle_agendabot_message y conversation_contexts
    # desde el app.py principal del core del bot.
    from agendabot.core.app import handle_agendabot_message, conversation_contexts
except ImportError as e:
    print(f"Error al importar handle_agendabot_message o conversation_contexts: {e}")
    print("Asegúrate de que la ruta de importación es correcta y que 'mi-portafolio-bots' está accesible.")
    sys.exit(1) # Salir si no se puede importar la lógica del bot

telegram_app = Flask(__name__)

# --- CONFIGURACIÓN DE TELEGRAM API (PLACEHOLDERS) ---
# Reemplaza esto con tu token real del Bot de Telegram (obtenido de BotFather)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN") # Reemplaza este PLACEHOLDER
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
            # Para esta demo, usamos el diccionario en memoria de app.py.
            current_context = conversation_contexts.get(chat_id, {
                "step": "welcome",
                "selected_service_code": None,
                "booking_details": {},
                "contact_info": {}
            })
            
            print(f"Telegram message from {chat_id}: {user_message}")

            # Procesar el mensaje con la lógica central del bot
            bot_response_result = handle_agendabot_message(user_message, current_context)
            bot_text_response = bot_response_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
            updated_context = bot_response_result.get('context', current_context)

            # Guardar el contexto actualizado (en una base de datos real en prod)
            conversation_contexts[chat_id] = updated_context
            
            # Enviar la respuesta a la API de Telegram
            send_telegram_message(chat_id, bot_text_response)
            
            return jsonify({"status": "success", "message": "Message processed"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a recognized Telegram update"}), 200

    except Exception as e:
        print(f"Error processing Telegram webhook: {e}", file=sys.stderr)
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
        print(f"Telegram message sent successfully to {chat_id}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message to {chat_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    # Este conector se ejecutaría como una app Flask independiente.
    # Necesitarías exponerlo públicamente (ej. con ngrok) para que Telegram lo alcance.
    port = int(os.environ.get('PORT', 5012)) # Usar un puerto diferente para Telegram
    telegram_app.run(host='0.0.0.0', port=port, debug=True)