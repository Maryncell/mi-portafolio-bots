# mi-portafolio-bots/healthbot/channels/telegram/telegram_connector.py

from flask import Flask, request, jsonify
import sys
import os
import requests
import json # Para manejar la estructura JSON de los datos del bot
from dotenv import load_dotenv # Para cargar variables de entorno

# Cargar variables de entorno (para TELEGRAM_BOT_TOKEN)
load_dotenv()

# --- Configuración para la importación del core del bot ---
# Calcula la ruta de la raíz del proyecto dinámicamente.
# Esto asume que este archivo está en mi-portafolio-bots/healthbot/channels/telegram/
current_dir = os.path.dirname(os.path.abspath(__file__))
# Sube tres niveles para llegar a mi-portafolio-bots/
# Por ejemplo:
# current_dir = .../mi-portafolio-bots/healthbot/channels/telegram
# os.path.join(current_dir, '..') = .../mi-portafolio-bots/healthbot/channels
# os.path.join(current_dir, '..', '..') = .../mi-portafolio-bots/healthbot
# os.path.join(current_dir, '..', '..', 'core') = .../mi-portafolio-bots/healthbot/core
# Esto es para que el adaptador pueda acceder a la lógica del bot.
# Sin embargo, dado que tu app.py ya es una API, no necesitamos importarlo directamente aquí.
# Solo necesitamos la URL.

healthbot_telegram_connector_app = Flask(__name__)

# --- CONFIGURACIÓN DE TELEGRAM API ---
# Reemplaza esto con el TOKEN REAL de tu BOT DE TELEGRAM para HealthBot
TELEGRAM_BOT_TOKEN = os.environ.get("HEALTHBOT_TELEGRAM_BOT_TOKEN") 
if not TELEGRAM_BOT_TOKEN:
    print("ADVERTENCIA: La variable de entorno HEALTHBOT_TELEGRAM_BOT_TOKEN no está configurada.", file=sys.stderr)
    print("El conector de Telegram no funcionará correctamente sin el token.", file=sys.stderr)
    # Puedes usar un token de prueba si estás desarrollando, pero no para producción.
    # TELEGRAM_BOT_TOKEN = "YOUR_FALLBACK_TELEGRAM_BOT_TOKEN"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"

# --- URL de tu backend HealthBot (app.py) ---
# Asegúrate de que esta URL sea accesible desde donde se ejecuta este conector.
# Si tu app.py está en localhost:5010, esta es la URL correcta.
HEALTHBOT_API_URL = "http://localhost:5010/api/healthbot_chat"

# --- Almacenamiento de contexto de conversación (simulado) ---
# En una aplicación real, esto se manejaría con una base de datos (Firestore, Redis, etc.)
# para persistir el contexto entre sesiones y usuarios.
# Aquí, lo usamos como un diccionario en memoria para demostración.
conversation_contexts = {}

# --- Webhook Principal de Telegram ---
@healthbot_telegram_connector_app.route('/webhook', methods=['POST'])
def telegram_message_webhook():
    data = request.get_json()
    print(f"Received Telegram data: {data}")

    try:
        chat_id = None
        user_message_text = None
        
        # Manejar mensajes de texto
        if 'message' in data and 'text' in data['message']:
            chat_id = data['message']['chat']['id']
            user_message_text = data['message']['text']
        # Manejar callbacks de botones (si usas botones inline en Telegram)
        elif 'callback_query' in data:
            chat_id = data['callback_query']['message']['chat']['id']
            user_message_text = data['callback_query']['data'] # El 'data' del botón es el 'mensaje'
            # Opcional: Responder al callback para quitar el "cargando" del botón
            requests.post(TELEGRAM_API_URL + "answerCallbackQuery", json={"callback_query_id": data['callback_query']['id']})

        if chat_id and user_message_text:
            # Obtener el contexto actual del usuario
            current_context = conversation_contexts.get(chat_id, {
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
            
            print(f"HealthBot Telegram message from {chat_id}: {user_message_text}")

            # Enviar el mensaje y el contexto a tu backend HealthBot
            healthbot_api_payload = {
                'message': user_message_text,
                'context': current_context,
                'user_id': str(chat_id) # Usar el chat_id de Telegram como user_id
            }
            
            healthbot_response = requests.post(HEALTHBOT_API_URL, json=healthbot_api_payload, timeout=30)
            healthbot_response.raise_for_status() # Lanza excepción para errores HTTP
            
            healthbot_result = healthbot_response.json()
            bot_text_response = healthbot_result.get('response', 'Lo siento, hubo un error procesando tu solicitud.')
            updated_context = healthbot_result.get('context', current_context)
            response_data = healthbot_result.get('data', None) # Datos adicionales como botones

            # Guardar el contexto actualizado
            conversation_contexts[chat_id] = updated_context
            
            # Enviar la respuesta a la API de Telegram, incluyendo botones si existen
            send_telegram_message(chat_id, bot_text_response, response_data)
            
            return jsonify({"status": "success", "message": "Message processed"}), 200
        
        return jsonify({"status": "ignored", "message": "Not a recognized Telegram update"}), 200

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con HealthBot API: {e}", file=sys.stderr)
        # Intentar enviar un mensaje de error al usuario de Telegram
        send_telegram_message(chat_id, "Lo siento, hubo un problema técnico al comunicarme con el asistente. Por favor, inténtalo más tarde.")
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        print(f"Error processing HealthBot Telegram webhook: {e}", file=sys.stderr)
        send_telegram_message(chat_id, "Lo siento, hubo un error inesperado. Por favor, inténtalo de nuevo.")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_telegram_message(chat_id, text_message, response_data=None):
    """
    Envía un mensaje de texto a Telegram usando la API de Bot,
    opcionalmente incluyendo botones de teclado de respuesta.
    """
    url = TELEGRAM_API_URL + "sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "parse_mode": "Markdown" # Telegram soporta negritas con Markdown (**)
    }
    
    reply_markup = {}
    if response_data and response_data.get('type') == 'action_buttons' and response_data.get('buttons'):
        keyboard_buttons = []
        for btn in response_data['buttons']:
            keyboard_buttons.append([{"text": btn['text'], "callback_data": btn['action']}])
            # Nota: Para ReplyKeyboardMarkup, 'callback_data' no se usa, solo 'text'.
            # Si quieres enviar el 'action' como un mensaje al bot, el usuario tendría que escribirlo.
            # Para que los botones envíen un "comando" al bot, usamos InlineKeyboardMarkup con callback_data.
            # Si quieres que el usuario "escriba" el texto del botón, usa ReplyKeyboardMarkup.
            # Para este caso, vamos a usar ReplyKeyboardMarkup para simular la web de forma más sencilla.
            # Si necesitas InlineKeyboardMarkup, la lógica cambia un poco.
            # Por ahora, para ReplyKeyboardMarkup, solo necesitamos el texto.
            # Si el frontend web envía "action" como el texto del botón, lo usamos.
            # Si "action" es un comando interno (ej. "confirmar_cita"), el usuario lo vería.
            # Es mejor que el "text" del botón sea lo que el usuario ve y lo que se envía.
            
            # Vamos a adaptar para que los botones del backend se usen como texto de ReplyKeyboardMarkup
            # Esto significa que el 'action' del backend se convierte en el 'text' del botón de Telegram.
            # Y el usuario lo "escribirá" al hacer clic.
            
            # Si el 'action' es un comando interno como 'confirmar_cita', el usuario lo vería.
            # Para que el usuario vea algo amigable pero el bot reciba el comando,
            # podemos usar InlineKeyboardMarkup con callback_data, o adaptar el backend
            # para que el 'text' del botón sea lo amigable y el 'action' sea el comando.
            # Por ahora, asumiremos que 'action' es lo que el bot necesita.
            
            # Para ReplyKeyboardMarkup, solo necesitamos el texto visible.
            # Si el 'action' es lo que queremos enviar, el 'text' debe ser lo que el usuario ve.
            # Lo más simple es que el 'action' sea el mismo que el 'text' para los botones de sugerencia.
            # Si el 'action' es un comando interno (ej. 'confirmar_cita'), el usuario lo verá.
            # Para evitar esto, deberíamos usar InlineKeyboardMarkup o adaptar la lógica del backend.

            # Opción 1: ReplyKeyboardMarkup (el usuario "escribe" el texto del botón)
            # Esto es lo más parecido a los botones de sugerencia de la web.
            keyboard_buttons.append([{"text": btn['text']}]) # Solo el texto visible

        if keyboard_buttons:
            # Puedes usar ReplyKeyboardMarkup para botones que el usuario "escribe"
            # o InlineKeyboardMarkup para botones con "callback_data" (más complejo para mantener el estado)
            # Por simplicidad y similitud con la web, usaremos ReplyKeyboardMarkup.
            reply_markup = {
                "keyboard": keyboard_buttons,
                "resize_keyboard": True,
                "one_time_keyboard": True # Opcional: el teclado desaparece después de un uso
            }
            payload["reply_markup"] = reply_markup
            
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"HealthBot Telegram message sent successfully to {chat_id}: {text_message}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending HealthBot Telegram message to {chat_id}: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'):
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return {"error": str(e)}

if __name__ == '__main__':
    # Este conector se ejecutaría como una app Flask independiente.
    # Necesitarías exponerlo públicamente (ej. con ngrok) para que Telegram lo alcance.
    # Asegúrate de que el puerto no entre en conflicto con tu app.py (5010).
    port = int(os.environ.get('TELEGRAM_CONNECTOR_PORT', 5007)) # Puerto diferente para Telegram (ej. 5007)
    print(f"Starting HealthBot Telegram Connector on port {port}...")
    healthbot_telegram_connector_app.run(host='0.0.0.0', port=port, debug=True)