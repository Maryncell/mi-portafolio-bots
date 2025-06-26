# channels/telegram/telegram_connector.py

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# URL del cerebro de Sellbot (tu app.py)
SELLBOT_CORE_URL = os.getenv("SELLBOT_CORE_URL", "http://localhost:5000/api/sellbot_chat")
# Tu token de bot de Telegram (obtenido de BotFather)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# Endpoint para recibir actualizaciones del webhook de Telegram
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = request.json
    print(f"Datos recibidos de Telegram: {update}")

    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        user_message_text = message.get('text', '')  # Puede que no siempre haya texto (ej. fotos)

        if user_message_text:
            # 1. Enviar el mensaje al núcleo de Sellbot
            sellbot_response = requests.post(SELLBOT_CORE_URL, json={
                'message': user_message_text,
                'context': {},  # En un entorno real, se almacenaría el contexto por chat_id
                'channel': 'telegram',
                'user_id': chat_id  # Pasar chat_id al core para rastreo
            }).json()

            response_text = sellbot_response.get('response', 'Lo siento, hubo un error en el bot.')
            response_data = sellbot_response.get('data')

            # 2. Formatear y enviar la respuesta de vuelta a Telegram
            telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": response_text,
                "parse_mode": "Markdown"  # Permite formato como negritas, cursivas
            }

            # Si hay datos estructurados, podemos añadir botones inline
            if response_data and response_data.get('type') in ['product_card', 'product_card_buy_options', 'simple_product_list']:
                inline_keyboard = []
                if response_data.get('type') == 'product_card_buy_options':
                    inline_keyboard.append([
                        {"text": "🛒 Añadir al carrito", "callback_data": f"add_to_cart_{response_data['code']}"},
                        {"text": "💰 Comprar ahora", "url": response_data.get('payment_link', '#')}
                    ])
                elif response_data.get('type') == 'simple_product_list':
                    # Ejemplo: Añadir un botón para cada producto para ver detalles
                    for product in response_data['products']:
                        inline_keyboard.append([{"text": f"Ver detalles de {product['name']}", "callback_data": f"details_{product['code']}"}])

                # Ejemplo de botones genéricos (como las sugerencias del HTML)
                inline_keyboard.append([
                    {"text": "Ver productos", "callback_data": "productos"},
                    {"text": "Rastrear pedido", "callback_data": "rastrear pedido"},
                ])

                payload['reply_markup'] = {
                    "inline_keyboard": inline_keyboard
                }

            # Enviar la respuesta a Telegram
            requests.post(telegram_api_url, json=payload)

    return jsonify({"status": "ok"}), 200

# Ejecutar el conector de Telegram
if __name__ == '__main__':
    # Usar un puerto diferente, por ejemplo 5002
    app.run(debug=True, port=5002)