# channels/instagram/instagram_connector.py

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# URL del cerebro de Sellbot (tu app.py)
SELLBOT_CORE_URL = os.getenv("SELLBOT_CORE_URL", "http://localhost:5000/api/sellbot_chat")
# Tu Page Access Token de Facebook/Instagram
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "YOUR_PAGE_ACCESS_TOKEN")
# Tu Verify Token (Webhook)
VERIFY_TOKEN_INSTAGRAM = os.getenv("VERIFY_TOKEN_INSTAGRAM", "YOUR_VERIFY_TOKEN")


# Endpoint para la verificación del webhook (GET request)
@app.route('/instagram-webhook', methods=['GET'])
def instagram_verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN_INSTAGRAM:
        print("Webhook de Instagram/Messenger verificado con éxito!")
        return challenge, 200
    else:
        print("Error de verificación del Webhook de Instagram/Messenger.")
        return jsonify({"status": "error", "message": "Verification token mismatch"}), 403

# Endpoint para recibir mensajes de Instagram/Messenger (POST request)
@app.route('/instagram-webhook', methods=['POST'])
def instagram_webhook():
    data = request.json
    print(f"Datos recibidos de Instagram/Messenger: {data}")

    if 'entry' in data:
        for entry in data['entry']:
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    sender_id = messaging_event['sender']['id'] # ID del usuario en Messenger/Instagram

                    if 'message' in messaging_event:
                        if 'text' in messaging_event['message']:
                            user_message_text = messaging_event['message']['text']
                            print(f"Mensaje de Instagram/Messenger de {sender_id}: {user_message_text}")

                            # 1. Enviar el mensaje al núcleo de Sellbot
                            sellbot_response = requests.post(SELLBOT_CORE_URL, json={
                                'message': user_message_text,
                                'context': {}, # En un entorno real, se almacenaría el contexto por sender_id
                                'channel': 'instagram',
                                'user_id': sender_id # Pasar sender_id al core para rastreo
                            }).json()
                            
                            response_text = sellbot_response.get('response', 'Lo siento, hubo un error en el bot.')
                            response_data = sellbot_response.get('data')

                            # 2. Formatear y enviar la respuesta de vuelta a Instagram/Messenger
                            # La API de Messenger es muy flexible para respuestas ricas.
                            # Aquí un ejemplo simple, pero podría ser mucho más complejo (carousel, quick replies)
                            message_payload = {
                                "recipient": {"id": sender_id},
                                "message": {"text": response_text}
                            }

                            if response_data and response_data.get('type') in ['product_card', 'product_card_buy_options']:
                                product = response_data
                                # Ejemplo de Quick Replies (botones de respuesta rápida)
                                message_payload['message']['quick_replies'] = [
                                    {"content_type": "text", "title": "Comprar", "payload": f"BUY_{product['code']}"},
                                    {"content_type": "text", "title": "Más detalles", "payload": f"DETAILS_{product['code']}"}
                                ]
                                # Podrías enviar un Template Message (ej. Generic Template para tarjeta de producto)
                                # message_payload['message'] = {
                                #     "attachment": {
                                #         "type": "template",
                                #         "payload": {
                                #             "template_type": "generic",
                                #             "elements": [{
                                #                 "title": product['name'],
                                #                 "image_url": product['image_url'],
                                #                 "subtitle": f"${product['price']:.2f} - {product['short_description']}",
                                #                 "buttons": [
                                #                     {"type": "web_url", "url": product.get('payment_link', '#'), "title": "Comprar Ahora"},
                                #                     {"type": "postback", "title": "Más Información", "payload": f"DETAILS_{product['code']}"}
                                #                 ]
                                #             }]
                                #         }
                                #     }
                                # }

                            requests.post(
                                f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
                                json=message_payload
                            )

    return jsonify({"status": "ok"}), 200

# Ejecutar el conector de Instagram/Messenger
if __name__ == '__main__':
    # Usar un puerto diferente, por ejemplo 5003
    app.run(debug=True, port=5003)