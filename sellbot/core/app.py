# C:\Users\User\Desktop\PP-chat\mi-portafolio-bots\app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import random
import re # Importar para expresiones regulares

# Inicializa la aplicación Flask.
app = Flask(__name__)
# Habilita CORS para permitir que tu frontend (demo_sellbot.html) pueda hacer solicitudes a este backend.
CORS(app)

# Simulación de una base de datos de productos.
# Añadimos 'image_url' y 'short_description' para respuestas más ricas en el frontend.
products_db = {
    "PC-GAMER-001": {
        "name": "PC Gamer Elite",
        "keywords": ["pc", "gamer", "elite", "ordenador", "computadora"],
        "price": 1200.00,
        "stock": 10,
        "image_url": "https://placehold.co/200x200/4c51bf/ffffff?text=PC+Gamer",
        "short_description": "Potente estación de juego para los más exigentes.",
        "features": ["Procesador Intel i9", "GPU NVIDIA RTX 4080", "32GB RAM DDR5", "1TB SSD NVMe", "Refrigeración líquida", "Iluminación RGB personalizable"]
    },
    "LAPTOP-PRO-002": {
        "name": "Laptop Profesional",
        "keywords": ["laptop", "notebook", "profesional", "portatil"],
        "price": 950.00,
        "stock": 5,
        "image_url": "https://placehold.co/200x200/4c51bf/ffffff?text=Laptop+Pro",
        "short_description": "Rendimiento y portabilidad para tu trabajo diario.",
        "features": ["Intel Core i7 13th Gen", "16GB RAM LPDDR5", "512GB SSD PCIe Gen4", "Pantalla 14\" QHD", "Batería de larga duración", "Teclado retroiluminado"]
    },
    "MONITOR-ULTRA-003": {
        "name": "Monitor Ultra HD",
        "keywords": ["monitor", "hd", "pantalla", "ultra", "visual"],
        "price": 300.00,
        "stock": 20,
        "image_url": "https://placehold.co/200x200/4c51bf/ffffff?text=Monitor+4K",
        "short_description": "Imágenes nítidas y colores vibrantes para una experiencia inmersiva.",
        "features": ["32 pulgadas 4K UHD", "Panel IPS", "HDR10", "FreeSync Premium", "Conectividad USB-C", "Base ergonómica"]
    },
    "TECLADO-RGB-004": {
        "name": "Teclado Mecánico RGB",
        "keywords": ["teclado", "mecanico", "rgb", "gaming"],
        "price": 75.00,
        "stock": 30,
        "image_url": "https://placehold.co/200x200/4c51bf/ffffff?text=Teclado+RGB",
        "short_description": "Precisión y estilo para tus sesiones de juego.",
        "features": ["Switches Cherry MX Red", "Iluminación RGB por tecla", "Reposamuñecas magnético", "Teclas PBT de doble inyección", "Software personalizable"]
    },
    "MOUSE-GAMER-005": {
        "name": "Mouse Gamer Óptico",
        "keywords": ["mouse", "raton", "gamer", "optico", "gaming"],
        "price": 40.00,
        "stock": 15,
        "image_url": "https://placehold.co/200x200/4c51bf/ffffff?text=Mouse+Gamer",
        "short_description": "Diseñado para la velocidad y exactitud en tus juegos.",
        "features": ["Sensor óptico de 16000 DPI", "6 botones programables", "Peso ajustable", "Iluminación RGB", "Cable trenzado de alta durabilidad"]
    },
}

# --- Funciones Auxiliares para la Lógica del Bot ---

def find_product_by_keyword(user_message):
    """Busca un producto en la base de datos por palabras clave del mensaje del usuario (mejorado)."""
    user_message_lower = user_message.lower()
    
    # 1. Buscar por código exacto o nombre exacto
    for code, product_info in products_db.items():
        if code.lower() == user_message_lower or product_info['name'].lower() == user_message_lower:
            return code
    
    # 2. Buscar por palabras clave o partes del nombre
    for code, product_info in products_db.items():
        for keyword in product_info['keywords']:
            if keyword in user_message_lower:
                return code
        if user_message_lower in product_info['name'].lower(): # Búsqueda de subcadenas
            return code
            
    return None

def get_product_details_response_data(product_code):
    """Genera datos estructurados de un producto para que el frontend los renderice."""
    product = products_db.get(product_code)
    if product:
        return {
            "type": "product_card",
            "name": product["name"],
            "code": product_code,
            "price": product["price"],
            "stock": product["stock"],
            "image_url": product["image_url"],
            "description": product["short_description"],
            "features": product["features"]
        }
    return None

def simulate_payment_process_link(product_name, price):
    """Simula un enlace de pago."""
    return f"https://checkout.mockup.com/pago/{product_name.replace(' ', '-')}-{price:.2f}"

def get_order_status_mock(order_id):
    """Simula el rastreo de un pedido."""
    mock_orders = {
        "12345": {"status": "En camino", "estimated_delivery": "2 días hábiles"},
        "67890": {"status": "Entregado", "estimated_delivery": "hace 1 día"},
        "11223": {"status": "Pendiente de envío", "estimated_delivery": "3-5 días hábiles"}
    }
    return mock_orders.get(order_id)

# --- Rutas del Chatbot ---

@app.route('/api/sellbot_chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').lower().strip()
    # Inicializa el contexto si es la primera interacción o viene de un reinicio
    current_context = data.get('context', {'step': 'welcome', 'last_queried_product_code': None, 'contact_info': {}})
    
    print(f"Mensaje recibido del usuario: '{user_message}' (Paso actual: {current_context.get('step')})")

    response_text = ""
    response_data = {} # Diccionario para enviar datos estructurados al frontend
    new_context = current_context.copy()
    current_step = new_context.get('step', 'welcome')

    # --- Manejo de reinicio / bienvenida / menú principal ---
    # Limpia el contexto completamente y reinicia si se detecta una intención de inicio/reinicio.
    if user_message in ["reiniciar simulacion", "menu principal", "hola", "inicio", "empezar", "reset", "cancelar"]:
        new_context = {'step': 'welcome', 'last_queried_product_code': None, 'contact_info': {}}
        response_text = "👋 ¡Hola! Soy Sellbot, tu asistente comercial. Estoy aquí para ayudarte con consultas sobre nuestros productos, stock, precios o tu pedido. ¿En qué puedo asistirte hoy?"
        return jsonify({"response": response_text, "context": new_context})

    # --- Flujos de Conversación basados en el Paso Actual (State Machine) ---
    # Priorizar flujos basados en estado para mantener la coherencia
    
    # Paso: Esperando el ID del pedido (después de preguntar por rastrear)
    if current_step == 'awaiting_order_id':
        if user_message.isdigit() and len(user_message) == 5: # Asumimos IDs de 5 dígitos
            order_status = get_order_status_mock(user_message)
            if order_status:
                response_text = (
                    f"✅ Tu pedido con número **{user_message}** se encuentra: **{order_status['status']}**. "
                    f"Se estima que la entrega será en: **{order_status['estimated_delivery']}**.\n\n"
                    "¿Necesitas algo más o quieres volver al menú principal?"
                )
                new_context['step'] = 'order_status_provided'
            else:
                response_text = (
                    f"❌ Lo siento, no encontré un pedido con el número **{user_message}**. "
                    "Por favor, verifica el número e inténtalo de nuevo. Si el problema persiste, puedo conectarte con un agente."
                )
                # El paso se mantiene en 'awaiting_order_id' para reintentar
        else:
            response_text = "Disculpa, el número de pedido no parece válido. Por favor, ingresa solo los 5 dígitos del número de seguimiento (ej. 12345)."
            # El paso se mantiene en 'awaiting_order_id'
        return jsonify({"response": response_text, "context": new_context})

    # Paso: Esperando el nombre del producto para una compra (después de "comprar" sin producto)
    if current_step == 'awaiting_product_name_for_purchase':
        product_code = find_product_by_keyword(user_message)
        if product_code:
            product = products_db[product_code]
            if product['stock'] > 0:
                payment_link = simulate_payment_process_link(product['name'], product['price'])
                response_text = (
                    f"Genial, aquí tienes los detalles de la **{product['name']}** y las opciones de compra:"
                )
                response_data = get_product_details_response_data(product_code) # Incluir datos del producto
                response_data['type'] = 'product_card_buy_options' # Nuevo tipo para el frontend
                response_data['payment_link'] = payment_link # Añadir el enlace de pago a los datos
                new_context['step'] = 'product_selected_for_purchase' # Transiciona a un nuevo paso para elegir comprar/añadir
            else:
                response_text = f"💔 Lo siento, la **{product['name']}** está agotada en este momento. ¿Te interesa otro producto de nuestro catálogo?"
                new_context['step'] = 'product_out_of_stock'
        else:
            response_text = "No logré identificar ese producto. Por favor, ¿podrías mencionar el nombre exacto o el código del producto que deseas comprar? (Ej. PC Gamer Elite, LAPTOP-PRO-002)"
            # El paso se mantiene en 'awaiting_product_name_for_purchase'
        return jsonify({"response": response_text, "context": new_context, "data": response_data})
    
    # Paso: Esperando el nombre del producto para una consulta (después de "stock" o "precio" sin producto)
    if current_step == 'awaiting_product_name_for_inquiry':
        product_code = find_product_by_keyword(user_message)
        if product_code:
            response_text = "Aquí tienes la información detallada que solicitaste:"
            response_data = get_product_details_response_data(product_code)
            new_context['step'] = 'product_info_provided'
        else:
            response_text = (
                "No encontré ese producto. Por favor, ¿podrías mencionar el nombre exacto o el código del producto para consultar stock, precio o descripción? "
                "Ejemplos: PC Gamer Elite, LAPTOP-PRO-002."
            )
            # El paso se mantiene en 'awaiting_product_name_for_inquiry'
        return jsonify({"response": response_text, "context": new_context, "data": response_data})

    # Paso: Recolectando datos de contacto para agente humano
    if current_step == 'collect_contact_for_human':
        # Intentar parsear nombre, email y teléfono
        name_match = re.search(r'(?:mi nombre es|soy|me llamo)\s+([a-zA-Z\s]+)', user_message)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message)
        phone_match = re.search(r'(\d{8,15})', user_message.replace(" ", "").replace("-", "")) # Busca 8-15 dígitos, quita espacios y guiones

        collected_name = name_match.group(1).strip() if name_match else None
        collected_email = email_match.group(0).strip() if email_match else None
        collected_phone = phone_match.group(0).strip() if phone_match else None

        # Si el usuario simplemente da "Nombre, email, telefono"
        if not (collected_name and collected_email and collected_phone):
            # Intentar parsear si el formato es "Nombre, Email, Telefono"
            parts = [p.strip() for p in user_message.split(',')]
            if len(parts) >= 3:
                temp_name = parts[0]
                temp_email = parts[1]
                temp_phone = parts[2]

                if re.match(r'[\w\.-]+@[\w\.-]+', temp_email):
                    collected_email = temp_email
                if re.match(r'(\d{8,15})', temp_phone.replace(" ", "").replace("-", "")):
                    collected_phone = temp_phone
                collected_name = temp_name # Asumir que el primero es el nombre
            
            # Caso de que solo se dé un email y/o teléfono, pero ya se pidió el nombre
            if 'temp_name_for_agent' in new_context and not collected_name:
                collected_name = new_context['temp_name_for_agent']

        # Almacenar info parcial si no está completa
        if collected_name: new_context['contact_info']['name'] = collected_name
        if collected_email: new_context['contact_info']['email'] = collected_email
        if collected_phone: new_context['contact_info']['phone'] = collected_phone

        final_name = new_context['contact_info'].get('name')
        final_email = new_context['contact_info'].get('email')
        final_phone = new_context['contact_info'].get('phone')

        if final_name and final_email and final_phone:
            response_text = (
                f"✅ ¡Gracias, **{final_name}**! Hemos recibido tus datos. "
                "Un asesor se pondrá en contacto contigo a la brevedad en tu email "
                f"({final_email}) o teléfono ({final_phone}).\n\n"
                "¿Necesitas algo más por el momento o quieres volver al menú principal?"
            )
            new_context['step'] = 'human_contact_collected'
            new_context['contact_info'] = {} # Limpiar info de contacto después de recolectarla
        else:
            missing_info = []
            if not final_name: missing_info.append("nombre")
            if not final_email: missing_info.append("email")
            if not final_phone: missing_info.append("número de teléfono")

            response_text = (
                f"Por favor, necesito tu **{', '.join(missing_info)}** para conectarte con un asesor. "
                "Asegúrate de incluirlos en tu mensaje.\n"
                "Ejemplo: 'Soy Juan Pérez, mi email es juan@ejemplo.com y mi teléfono es 1123456789'."
            )
            # El paso se mantiene en 'collect_contact_for_human'
        return jsonify({"response": response_text, "context": new_context})

    # Paso: Manejo de respuesta a FAQ Topic
    if current_step == 'awaiting_faq_topic':
        if "envio" in user_message or "shipping" in user_message:
            response_text = "🚚 **Políticas de Envío:** Nuestros costos y tiempos de envío varían. Ofrecemos envío estándar gratuito a partir de cierto monto y opciones express con costo. Puedes ver los detalles aquí: [Link a Políticas de Envío Falsas].\n\n"
            new_context['step'] = 'faq_answered_prompt' # Nuevo estado para preguntar si quiere más FAQ
        elif "devolucion" in user_message or "cambio" in user_message or "retorno" in user_message:
            response_text = "↩️ **Políticas de Devolución:** Tienes 30 días para cambios o devoluciones si el producto está en su empaque original y sin uso. Más info: [Link a Políticas de Devolución Falsas].\n\n"
            new_context['step'] = 'faq_answered_prompt' # Nuevo estado para preguntar si quiere más FAQ
        elif "pago" in user_message or "metodos de pago" in user_message or "formas de pago" in user_message:
            response_text = "💳 **Métodos de Pago:** Aceptamos tarjetas de crédito/débito (Visa, MasterCard, Amex) y opciones en cuotas. Próximamente habilitaremos transferencias bancarias. ¿Cuál te interesa usar?\n\n"
            new_context['step'] = 'faq_answered_prompt' # Nuevo estado para preguntar si quiere más FAQ
        else:
            response_text = "No entendí tu pregunta sobre las FAQ. Por favor, selecciona un tema como 'Envío', 'Devolución' o 'Pago' o escribe 'cancelar' para volver al menú principal."
            # El paso se mantiene en 'awaiting_faq_topic'
        return jsonify({"response": response_text, "context": new_context})

    # Nuevo Paso: Después de responder una FAQ, preguntar si quiere más o volver al menú principal
    if current_step == 'faq_answered_prompt':
        if "si" in user_message or "sí" in user_message or "otro tema" in user_message or "mas preguntas" in user_message:
            response_text = (
                "📄 ¡Claro! Estoy aquí para ayudarte con nuestras **Preguntas Frecuentes**.\n"
                "¿Sobre qué tema te gustaría saber más?\n"
                "• **Políticas de Envío**\n"
                "• **Políticas de Devolución**\n"
                "• **Métodos de Pago**\n\n"
                "Puedes hacer clic en un botón o escribir tu pregunta."
            )
            new_context['step'] = 'awaiting_faq_topic'
        else: # Cualquier otra respuesta lo lleva al menú principal
            response_text = "De acuerdo. Si necesitas algo más, no dudes en preguntar."
            new_context['step'] = 'main_menu'
        return jsonify({"response": response_text, "context": new_context})


    # --- Intenciones Primarias (sin un paso específico previo) ---
    # Orden de prioridad: Human > FAQ > Rastreo > Productos/Compras > General

    # Intención: Transferencia a Agente Humano (Alta prioridad para no ser interceptado por otras reglas)
    if "humano" in user_message or "agente" in user_message or "soporte" in user_message or "ayuda personalizada" in user_message:
        response_text = (
            "🤝 Entiendo perfectamente. Para una atención más personalizada con uno de nuestros asesores, "
            "por favor, déjame tu **nombre completo, email y número de teléfono** "
            "(con código de área) en un solo mensaje. "
            "Esto nos ayudará a contactarte de forma eficiente.\n\n"
            "Ejemplo: 'Soy Juan Pérez, mi email es juan@ejemplo.com y mi teléfono es 1123456789'."
        )
        new_context['step'] = 'collect_contact_for_human'
        new_context['contact_info'] = {} # Limpiar cualquier info de contacto previa
        return jsonify({"response": response_text, "context": new_context})

    # Intención: FAQs Generales (Prioridad alta para que funcione bien)
    elif "preguntas frecuentes" in user_message or "faqs" in user_message or "informacion general" in user_message or "politicas" in user_message:
        response_text = (
            "📄 ¡Claro! Estoy aquí para ayudarte con nuestras **Preguntas Frecuentes**.\n"
            "¿Sobre qué tema te gustaría saber más?\n"
            "• **Políticas de Envío**\n"
            "• **Políticas de Devolución**\n"
            "• **Métodos de Pago**\n\n"
            "Puedes hacer clic en un botón o escribir tu pregunta."
        )
        new_context['step'] = 'awaiting_faq_topic'
        return jsonify({"response": response_text, "context": new_context})


    # Intención: Rastreo de Pedido (Prioridad media)
    elif "rastrear" in user_message or "pedido" in user_message or "donde esta mi pedido" in user_message or "seguimiento" in user_message:
        response_text = "🔍 ¡Claro! Para rastrear tu pedido, por favor, proporciónanos tu **número de seguimiento de 5 dígitos** (ej. 12345)."
        new_context['step'] = 'awaiting_order_id' # Espera el ID del pedido
        return jsonify({"response": response_text, "context": new_context})


    # Intención: Consultar Catálogo de Productos
    elif "productos" in user_message or "catalogo" in user_message or "que venden" in user_message or "lista de productos" in user_message:
        # Aquí solo enviamos una lista de nombres/códigos para el frontend
        products_list_simple = []
        for code, product_info in products_db.items():
            products_list_simple.append({"name": product_info["name"], "code": code})
        
        response_text = "🚀 ¡Claro! Tenemos una increíble selección de tecnología. Aquí te muestro nuestros productos principales. Si te interesa alguno, puedes mencionarlo por su nombre o código para ver más detalles:"
        response_data = {"type": "simple_product_list", "products": products_list_simple} # Nuevo tipo para el frontend
        new_context['step'] = 'product_list_provided'
        return jsonify({"response": response_text, "context": new_context, "data": response_data})


    # Intención: Consulta de Detalles de Producto (Precio, Stock, Descripción)
    elif any(keyword in user_message for keyword in ["stock", "precio", "costo", "cuanto vale", "descripcion", "detalles", "ver mas"]) or current_step == 'product_list_provided': # Si viene de listar productos
        product_code = find_product_by_keyword(user_message)
        if product_code:
            response_text = "Aquí tienes la información detallada que solicitaste:"
            response_data = get_product_details_response_data(product_code)
            new_context['step'] = 'product_info_provided'
        else:
            response_text = (
                "🧐 Para darte la información exacta, necesito saber el producto. "
                "¿De qué producto quieres saber el stock, precio o descripción? "
                "Puedes decir su nombre (ej. Laptop Profesional) o su código (ej. PC-GAMER-001)."
            )
            new_context['step'] = 'awaiting_product_name_for_inquiry' # Solicita el nombre del producto
        return jsonify({"response": response_text, "context": new_context, "data": response_data})


    # Intención: Añadir al Carrito (El backend solo confirma, el frontend gestiona el carrito)
    elif "añadir al carrito" in user_message or "agregar al carrito" in user_message:
        product_code = find_product_by_keyword(user_message)
        if product_code:
            product = products_db[product_code]
            response_text = (
                f"✅ ¡**{product['name']}** ha sido añadido a tu carrito! "
                "Puedes seguir explorando o ver tu carrito para finalizar la compra."
            )
            # Enviar datos del producto para que el frontend lo añada al carrito
            response_data = {"type": "add_to_cart_confirmation", "product": get_product_details_response_data(product_code)}
            new_context['step'] = 'product_added_to_cart'
        else:
            response_text = "Disculpa, no logré identificar qué producto deseas añadir al carrito. ¿Puedes mencionarlo por su nombre o código?"
            new_context['step'] = 'awaiting_product_name_for_inquiry' # Podría ser para compra o solo consulta
        return jsonify({"response": response_text, "context": new_context, "data": response_data})


    # Intención: Iniciar Compra (Desencadena el flujo de compra guiada o directa si ya hay producto)
    elif "comprar" in user_message or "quiero este" in user_message or "checkout" in user_message or "finalizar compra" in user_message:
        product_code = find_product_by_keyword(user_message)
        if product_code:
            product = products_db[product_code]
            if product['stock'] > 0:
                product['stock'] -= 1 # Simula la reducción de stock
                payment_link = simulate_payment_process_link(product['name'], product['price'])
                response_text = (
                    f"🛒 ¡Excelente elección! La **{product['name']}** está disponible.\n"
                    f"Puedes proceder al pago seguro a través de este enlace: {payment_link}\n\n"
                    f"¡Gracias por tu compra! Stock restante: {product['stock']} unidades."
                )
                response_data = get_product_details_response_data(product_code) # Incluir datos del producto
                response_data['type'] = 'purchase_confirmation' # Tipo específico para el frontend
                response_data['payment_link'] = payment_link # Añadir el enlace de pago a los datos
                new_context['step'] = 'purchase_completed'
            else:
                response_text = f"💔 Lo siento, la **{product['name']}** está agotada en este momento. ¿Te interesa otro producto de nuestro catálogo?"
                new_context['step'] = 'product_out_of_stock'
        else:
            response_text = "Para ayudarte con la compra, ¿qué producto te gustaría adquirir? Por favor, menciona su nombre o código."
            new_context['step'] = 'awaiting_product_name_for_purchase' # Pide el nombre del producto para compra
        return jsonify({"response": response_text, "context": new_context, "data": response_data})


    # Intención: Despedida / Agradecimiento
    elif "gracias" in user_message or "chau" in user_message or "adios" in user_message or "bye" in user_message:
        response_text = "😊 ¡De nada! Fue un placer ayudarte. Si tienes más preguntas, no dudes en consultarme. ¡Que tengas un excelente día!"
        new_context['step'] = 'goodbye'
        return jsonify({"response": response_text, "context": new_context})

    # --- Fallback (Si ninguna intención fue reconocida) ---
    response_text = (
        "😕 Disculpa, no logré entender tu consulta. Soy Sellbot, tu asistente para ventas. "
        "Mis funciones principales son:\n"
        "• **Ver productos:** (ej. 'productos', 'precio Laptop Profesional')\n"
        "• **Rastrear pedidos:** (ej. 'rastrear mi pedido 12345')\n"
        "• **Preguntas frecuentes:** (ej. 'preguntas frecuentes', 'políticas de envío')\n"
        "• **Conectarte con un asesor:** (ej. 'hablar con un humano')\n\n"
        "¿En qué te puedo asistir específicamente?"
    )
    new_context['step'] = 'main_menu' # Vuelve al menú principal si la confusión es alta
    return jsonify({"response": response_text, "context": new_context, "data": response_data})


# Inicia el servidor Flask en el puerto 5000 si el script se ejecuta directamente.
if __name__ == '__main__':
    app.run(debug=True, port=5000)