# mi-portafolio-bots/edubot/core/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import os
import sys
import unicodedata # Importar para la normalización de cadenas (ej. quitar acentos)

# Inicializa la aplicación Flask.
app = Flask(__name__)
# Habilita CORS para permitir que tu frontend (demo_agente_educativo.html) pueda hacer solicitudes a este backend.
CORS(app)

# --- Base de Datos Simulada de Cursos y FAQs Educativas ---
courses_db = {
    "ENG101": {
        "name": "Inglés para Principiantes A1",
        "keywords": ["ingles", "principiantes", "a1", "idiomas", "english"],
        "duration": "3 meses (48 horas)",
        "start_dates": ["01/09/2025", "01/12/2025"],
        "requirements": "Ninguno, solo ganas de aprender.",
        "certification": "Certificado de Nivel A1 (avalado por nuestra institución).",
        "price": 150.00,
        "description": "Curso intensivo y práctico para adquirir las bases del inglés, enfocado en conversación y comprensión auditiva para el día a día.",
        "curriculum": [
            "Introducción y Saludos",
            "Números y Colores",
            "Presente Simple y Continuo",
            "Vocabulario de Viajes y Compras",
            "Práctica de Conversación Básica",
            "Cultura General Anglosajona"
        ],
        "image_url": "https://placehold.co/200x200/22c55e/ffffff?text=Ingles+A1" # emerald-500
    },
    "PROG201": {
        "name": "Introducción a Python",
        "keywords": ["python", "programacion", "coding", "introduccion", "programar"],
        "duration": "2 meses (32 horas)",
        "start_dates": ["15/10/2025", "15/01/2026"],
        "requirements": "Conocimientos básicos de computación (uso de PC, internet).",
        "certification": "Certificado de Programador Python Junior.",
        "price": 250.00,
        "description": "Aprende los fundamentos de la programación desde cero con Python, el lenguaje más popular y versátil.",
        "curriculum": [
            "Variables y Tipos de Datos",
            "Operadores y Expresiones",
            "Estructuras de Control (if/else, for, while)",
            "Funciones y Módulos",
            "Manejo de Archivos",
            "Introducción a POO"
        ],
        "image_url": "https://placehold.co/200x200/ef4444/ffffff?text=Python" # red-500
    },
    "MKT301": {
        "name": "Marketing Digital Avanzado",
        "keywords": ["marketing", "digital", "avanzado", "estrategia", "publicidad"],
        "duration": "4 meses (60 horas)",
        "start_dates": ["01/11/2025"],
        "requirements": "Haber completado un curso de Marketing Digital básico o tener experiencia laboral comprobable.",
        "certification": "Certificado de Especialista en Marketing Digital Estratégico.",
        "price": 400.00,
        "description": "Domina las estrategias y herramientas de marketing digital más modernas para impulsar negocios y marcas.",
        "curriculum": [
            "SEO Avanzado y SEM",
            "Marketing de Contenidos y Storytelling",
            "Publicidad en Redes Sociales (Meta Ads, Google Ads)",
            "Email Marketing y Automatización",
            "Analítica Web con Google Analytics 4",
            "Estrategias de Growth Hacking"
        ],
        "image_url": "https://placehold.co/200x200/3b82f6/ffffff?text=Marketing+Digital" # blue-500
    }
}

# FAQs con claves que intentaremos normalizar para mejor coincidencia
faqs_edu = {
    "horarios": "Nuestros cursos ofrecen horarios flexibles. Las clases en vivo se dictan en diferentes franjas horarias y siempre quedan grabadas para que las veas cuando quieras. ¿Necesitas saber los horarios de un curso en particular?",
    "pagos": "Puedes pagar con tarjeta de crédito/débito (Visa, Mastercard, Amex), transferencia bancaria o a través de plataformas como Mercado Pago. Ofrecemos planes de cuotas sin interés. Para más detalles, visita nuestro portal de pagos: [Link al Portal de Pagos Falso](https://example.com/pagos).",
    "profesores": "Contamos con un equipo de docentes altamente calificados, profesionales activos en sus respectivas industrias, garantizando una enseñanza práctica y actualizada. Puedes ver sus perfiles en la sección 'Nuestro Equipo' de la web.",
    "plataformas": "Utilizamos Moodle como nuestra plataforma principal para acceder a materiales, foros y actividades. Las clases en vivo se imparten a través de Zoom o Google Meet.",
    "materiales": "Todos los materiales de estudio (apuntes, lecturas, ejercicios, recursos adicionales) están incluidos en el costo del curso y son accesibles digitalmente desde nuestra plataforma.",
    "reglamentos": "El reglamento estudiantil completo, que incluye políticas de asistencia, evaluación y convivencia, está disponible para consulta en la sección 'Términos y Condiciones' o 'Reglamento Académico' de nuestro sitio web.",
    "inscripcion": "El proceso de inscripción es 100% online. Primero, elige tu curso ideal. Luego, completa el formulario de pre-inscripción y, finalmente, efectúa el pago para asegurar tu cupo. ¿Ya sabes qué curso te interesa para inscribirte?",
    "certificaciones": "Al completar y aprobar satisfactoriamente el curso, se te emitirá un certificado digital de participación y aprobación, con la carga horaria y el contenido del curso, avalado por nuestra institución.",
    "prerrequisitos": "Los prerrequisitos varían según el curso. Para darte la información exacta, por favor, dime el nombre o código del curso que te interesa. Te puedo ayudar si me dices el nombre del curso, por ejemplo 'prerrequisitos para Inglés A1'.",
}

# --- Estado de la Conversación (simulado) ---
conversation_contexts = {}

# --- Funciones Auxiliares para la Lógica del Bot ---

def normalize_text(text):
    """Normaliza el texto para INTENCIONES y búsqueda de KEYWORDS: a minúsculas, quita acentos y caracteres especiales."""
    if not isinstance(text, str): 
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    # Modificación para permitir guiones bajos en la normalización para comandos internos
    text = re.sub(r'[^a-z0-9\s_]', '', text) # Solo letras, números, espacios y guiones bajos
    return text

def find_course_by_keyword(user_message):
    """Busca un curso en la base de datos por palabras clave del mensaje del usuario."""
    user_message_normalized = normalize_text(user_message)

    # 1. Búsqueda por código exacto o nombre completo normalizado
    for code, course_info in courses_db.items():
        if normalize_text(code) == user_message_normalized or normalize_text(course_info['name']) == user_message_normalized:
            return code
    
    # 2. Búsqueda por palabra clave o parte del nombre
    for code, course_info in courses_db.items():
        # Comprobar si alguna palabra clave está en el mensaje normalizado
        if any(normalize_text(kw) in user_message_normalized for kw in course_info['keywords']):
            return code
        # Comprobar si el nombre normalizado del curso está en el mensaje normalizado (parcial)
        if normalize_text(course_info['name']) in user_message_normalized:
            return code
            
    return None

def get_course_details_response_data(course_code):
    """Genera datos estructurados de un curso para que el frontend los renderice."""
    course = courses_db.get(course_code)
    if course:
        return {
            "type": "course_card",
            "name": course["name"],
            "code": course_code,
            "price": course["price"],
            "duration": course["duration"],
            "start_dates": course["start_dates"],
            "requirements": course["requirements"],
            "certification": course["certification"],
            "description": course["description"],
            "curriculum": course["curriculum"],
            "image_url": course["image_url"]
        }
    return None

def simulate_enrollment_link(course_name, price):
    """Simula un enlace de inscripción/pago."""
    formatted_course_name = re.sub(r'[^\w\s-]', '', course_name).replace(' ', '-').lower()
    return f"https://enroll.mockup.com/inscripcion/{formatted_course_name}-{price:.2f}"

def validate_email(email_str):
    """Valida un formato básico de correo electrónico."""
    # Se valida sobre el string original, no el normalizado.
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_str)

def validate_phone_number(phone_str):
    """Valida un formato básico de número de teléfono (solo dígitos, opcional + al inicio)."""
    # Se valida sobre el string original o una versión con solo digitos/+, no la normalizada.
    cleaned_number = re.sub(r'[^\d+]', '', phone_str)
    return re.match(r'^\+?\d{8,15}$', cleaned_number)

# --- Lógica Principal del Bot (handle_edubot_message) ---
def handle_edubot_message(user_message, current_context):
    response_text = ""
    response_data = {}
    new_context = current_context.copy()
    current_step = new_context.get('step', 'welcome')
    
    # user_message_normalized se usa solo para INTENCIONES y búsqueda de KEYWORDS
    # NO para validación de formato (emails, teléfonos)
    user_message_normalized = normalize_text(user_message)

    print(f"DEBUG_EDUBOT: Mensaje recibido: '{user_message}' (Normalizado para intenciones: '{user_message_normalized}', Paso actual: {current_step})")

    # --- Manejo de reinicio / bienvenida / menú principal ---
    if user_message_normalized in ["reiniciar", "menu principal", "hola", "inicio", "empezar", "reset", "cancelar"]:
        new_context = {'step': 'welcome', 'last_queried_course_code': None, 'contact_info': {}}
        response_text = "👋 ¡Hola! Soy **Edubot**, tu Agente Educativo Automatizado. Estoy aquí para ayudarte con información sobre nuestros cursos, el proceso de inscripción y preguntas frecuentes. ¿En qué puedo asistirte hoy?"
        response_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver Cursos", "action": "cursos"},
            {"text": "Inscribirme", "action": "inscribirme"},
            {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"},
            {"text": "Reiniciar", "action": "reiniciar"}
        ]}
        return {"response": response_text, "context": new_context, "data": response_data}

    # --- Manejo de comandos explícitos de botones (ALTA PRIORIDAD) ---
    # Esto debe ir ANTES de cualquier normalización de intención general
    if user_message_normalized.startswith("inscribirme_curso_"):
        course_code = user_message_normalized.replace("inscribirme_curso_", "").strip().upper()
        if course_code in courses_db:
            new_context['step'] = 'awaiting_enrollment_name'
            new_context['last_queried_course_code'] = course_code
            response_text = f"¡Excelente! Para inscribirte en **{courses_db[course_code]['name']}**, por favor, dime tu nombre completo."
        else:
            response_text = "Disculpa, no pude identificar el curso al que quieres inscribirte. Por favor, intenta de nuevo."
            new_context['step'] = 'main_menu'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Ver Cursos", "action": "cursos"},
                {"text": "Inscribirme", "action": "inscribirme"}
            ]}
        return {"response": response_text, "context": new_context, "data": response_data}

    if user_message_normalized.startswith("info_curso_"):
        course_code = user_message_normalized.replace("info_curso_", "").strip().upper()
        if course_code in courses_db:
            response_text = "Aquí tienes más detalles del curso que solicitaste:"
            response_data = get_course_details_response_data(course_code)
            new_context['step'] = 'course_info_provided'
            # Botones mejorados después de mostrar una tarjeta de curso
            response_data['buttons'] = [
                {"text": f"Inscribirme en {courses_db[course_code]['name']}", "action": f"inscribirme_curso_{course_code}"},
                {"text": "Ver otros cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Menú principal", "action": "menu principal"}
            ]
        else:
            response_text = "Disculpa, no pude encontrar información para ese curso. Por favor, intenta de nuevo."
            new_context['step'] = 'main_menu'
        return {"response": response_text, "context": new_context, "data": response_data}


    # --- Flujos de Conversación basados en el Paso Actual (State Machine) ---
    
    # Paso: Esperando nombre del curso para inscripción (si no vino de botón explícito)
    if current_step == 'awaiting_course_for_enrollment':
        course_code = find_course_by_keyword(user_message_normalized)
        if course_code:
            new_context['step'] = 'awaiting_enrollment_name'
            new_context['last_queried_course_code'] = course_code
            response_text = f"¡Perfecto! Para inscribirte en **{courses_db[course_code]['name']}**, por favor, dime tu nombre completo."
        else:
            response_text = "No logré identificar ese curso. ¿Podrías mencionar el nombre exacto o el código del curso en el que te quieres inscribir? (Ej. Inglés para Principiantes A1, PROG201)"
            # El paso se mantiene en 'awaiting_course_for_enrollment' para reintentar
        return {"response": response_text, "context": new_context, "data": response_data}

    # FLUJO DE INSCRIPCIÓN GUIADA
    if current_step == 'awaiting_enrollment_name':
        new_context['contact_info']['name'] = user_message.title() # Captura el nombre tal cual, capitalizado
        new_context['step'] = 'awaiting_enrollment_email'
        response_text = "Gracias. Ahora, por favor, proporciona tu dirección de correo electrónico."
        return {"response": response_text, "context": new_context, "data": response_data}

    if current_step == 'awaiting_enrollment_email':
        # VALIDACIÓN CLAVE: Se usa user_message ORIGINAL, NO el normalizado.
        if validate_email(user_message): 
            new_context['contact_info']['email'] = user_message.lower() # Guarda en minúsculas
            course_code = new_context.get('last_queried_course_code')
            course_name = courses_db[course_code]['name'] if course_code else "el curso seleccionado"
            course_price = courses_db[course_code]['price'] if course_code else 0

            enrollment_link = simulate_enrollment_link(course_name, course_price)
            response_text = (
                f"¡Perfecto, **{new_context['contact_info']['name']}**! Hemos registrado tu interés en **{course_name}** ({new_context['contact_info']['email']}). "
                f"Para completar tu inscripción, por favor, rellena nuestro formulario oficial aquí: [Formulario de Inscripción Falso]({enrollment_link}).\n\n"
                "Te enviaremos un email con los próximos pasos."
            )
            new_context['step'] = 'enrollment_completed'
            new_context['contact_info'] = {} # Limpiar info de contacto
            new_context['last_queried_course_code'] = None # Limpiar el curso en contexto
            # Añadir botones después de completar la inscripción
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Ver Cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Hablar con un asesor", "action": "hablar con un asesor"},
                {"text": "Reiniciar", "action": "reiniciar"}
            ]}
        else:
            response_text = "Ese no parece ser un correo electrónico válido. Por favor, ingresa una dirección de correo electrónico válida (ej. tunombre@ejemplo.com)."
            # Se mantiene en 'awaiting_enrollment_email'
        return {"response": response_text, "context": new_context, "data": response_data}


    # Paso: Esperando nombre del curso para información detallada (si no vino de botón explícito)
    if current_step == 'awaiting_course_for_info':
        course_code = find_course_by_keyword(user_message_normalized)
        if course_code:
            response_text = "Aquí tienes la información detallada que solicitaste:"
            response_data = get_course_details_response_data(course_code)
            new_context['step'] = 'course_info_provided'
            # Botones mejorados después de mostrar una tarjeta de curso
            response_data['buttons'] = [
                {"text": f"Inscribirme en {courses_db[course_code]['name']}", "action": f"inscribirme_curso_{course_code}"},
                {"text": "Ver otros cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Menú principal", "action": "menu principal"}
            ]
        else:
            response_text = "No encontré ese curso. Por favor, ¿podrías mencionar el nombre exacto o el código del curso para darte sus detalles? (Ej. Introducción a Python, ENG101)"
            # El paso se mantiene en 'awaiting_course_for_info'
        return {"response": response_text, "context": new_context, "data": response_data}

    # Paso: Recolectando datos de contacto para agente humano
    if current_step == 'collect_contact_for_human':
        if 'contact_info' not in new_context or not isinstance(new_context['contact_info'], dict):
            new_context['contact_info'] = {}

        # Intentar extraer email y teléfono del user_message ORIGINAL
        # Regex para email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', user_message) 
        # Regex para telefono
        phone_match = re.search(r'(\+?\d[\d\s\-\(\)]{7,20})', user_message) 
        
        # Validar y almacenar
        collected_email = email_match.group(0).strip() if email_match and validate_email(email_match.group(0)) else None
        collected_phone = phone_match.group(0).strip() if phone_match and validate_phone_number(phone_match.group(0)) else None

        # Intentar extraer nombre (si no se hizo antes con regex específico)
        name_match = re.search(r'(?:mi nombre es|soy|me llamo)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)', user_message)
        collected_name = name_match.group(1).strip().title() if name_match else None

        # Si no se encontró todo con regex, intentar con split (menos robusto)
        if not (collected_name and collected_email and collected_phone):
            parts = [p.strip() for p in user_message.split(',')]
            if len(parts) >= 3:
                temp_name = parts[0].title() # Capitalizar nombre
                temp_email = parts[1]
                temp_phone = parts[2]

                if not collected_name: collected_name = temp_name
                if not collected_email and validate_email(temp_email): collected_email = temp_email
                if not collected_phone and validate_phone_number(temp_phone): collected_phone = temp_phone
            
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
            new_context['contact_info'] = {} # Limpiar info de contacto
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Ver Cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Hablar con un asesor", "action": "hablar con un asesor"},
                {"text": "Reiniciar", "action": "reiniciar"}
            ]}
        else:
            missing_info = []
            if not final_name: missing_info.append("nombre")
            if not final_email: missing_info.append("email")
            if not final_phone: missing_info.append("número de teléfono")

            response_text = (
                f"Por favor, necesito tu **{', '.join(missing_info)}** para conectarte con un asesor. "
                "Asegúrate de incluirlos en tu mensaje.\n"
                "Ejemplo: 'Soy Ana García, mi email es ana@ejemplo.com y mi teléfono es +5491112345678'."
            )
        return {"response": response_text, "context": new_context, "data": response_data}


    # Paso: Manejo de respuesta a FAQ Educativa o solicitud directa de FAQ
    if current_step == 'awaiting_edu_faq_topic' or any(normalize_text(topic) in user_message_normalized for topic in faqs_edu.keys()):
        
        found_faq_topic = None
        for topic_key, _ in faqs_edu.items():
            if normalize_text(topic_key) in user_message_normalized:
                found_faq_topic = topic_key
                break
        
        if found_faq_topic:
            if found_faq_topic == "prerrequisitos":
                response_text = faqs_edu["prerrequisitos"]
                new_context['step'] = 'awaiting_course_for_info_prereq'
                response_data = {"type": "action_buttons", "buttons": [
                    {"text": "Requisitos de Inglés A1", "action": "info_curso_ENG101"},
                    {"text": "Requisitos de Python", "action": "info_curso_PROG201"},
                    {"text": "Ver todos los cursos", "action": "cursos"},
                    {"text": "Cancelar", "action": "cancelar"}
                ]}
            else:
                response_text = faqs_edu[found_faq_topic] + "\n\n¿Hay algo más sobre lo que te gustaría preguntar o quieres volver al menú principal?"
                new_context['step'] = 'edu_faq_answered_prompt'
                response_data = {"type": "action_buttons", "buttons": [
                    {"text": "Sí, otra pregunta", "action": "preguntas frecuentes"},
                    {"text": "Menú principal", "action": "menu principal"}
                ]}
        else:
            response_text = (
                "📄 ¡Claro! Estoy aquí para ayudarte con nuestras **Preguntas Frecuentes**.\n"
                "¿Sobre qué tema te gustaría saber más?\n"
                "• **Horarios**\n"
                "• **Pagos**\n"
                "• **Profesores**\n"
                "• **Plataformas**\n"
                "• **Materiales**\n"
                "• **Reglamentos**\n"
                "• **Inscripción**\n"
                "• **Certificaciones**\n"
                "• **Prerrequisitos**\n\n"
                "Puedes hacer clic en un botón o escribir tu pregunta."
            )
            new_context['step'] = 'awaiting_edu_faq_topic'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Horarios", "action": "horarios"},
                {"text": "Pagos", "action": "pagos"},
                {"text": "Profesores", "action": "profesores"},
                {"text": "Plataformas", "action": "plataformas"},
                {"text": "Materiales", "action": "materiales"},
                {"text": "Reglamentos", "action": "reglamentos"},
                {"text": "Inscripción", "action": "inscripcion"},
                {"text": "Certificaciones", "action": "certificaciones"},
                {"text": "Prerrequisitos", "action": "prerrequisitos"},
                {"text": "Cancelar", "action": "cancelar"}
            ]}
        return {"response": response_text, "context": new_context, "data": response_data}

    # Nuevo Paso: Después de responder una FAQ, preguntar si quiere más o volver al menú principal
    if current_step == 'edu_faq_answered_prompt':
        if "si" in user_message_normalized or "otro tema" in user_message_normalized or "mas preguntas" in user_message_normalized or "preguntas frecuentes" in user_message_normalized:
            response_text = (
                "📄 ¡Claro! Estoy aquí para ayudarte con nuestras **Preguntas Frecuentes**.\n"
                "¿Sobre qué tema te gustaría saber más?\n"
                "• **Horarios**\n"
                "• **Pagos**\n"
                "• **Profesores**\n"
                "• **Plataformas**\n"
                "• **Materiales**\n"
                "• **Reglamentos**\n"
                "• **Inscripción**\n"
                "• **Certificaciones**\n"
                "• **Prerrequisitos**\n\n"
                "Puedes hacer clic en un botón o escribir tu pregunta."
            )
            new_context['step'] = 'awaiting_edu_faq_topic'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Horarios", "action": "horarios"},
                {"text": "Pagos", "action": "pagos"},
                {"text": "Profesores", "action": "profesores"},
                {"text": "Inscripción", "action": "inscripcion"},
                {"text": "Prerrequisitos", "action": "prerrequisitos"},
                {"text": "Cancelar", "action": "cancelar"}
            ]}
        else: # Cualquier otra respuesta lo lleva al menú principal
            response_text = "De acuerdo. Si necesitas algo más, no dudes en preguntar."
            new_context['step'] = 'main_menu'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Ver Cursos", "action": "cursos"},
                {"text": "Inscribirme", "action": "inscribirme"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Hablar con un asesor", "action": "hablar con un asesor"},
                {"text": "Reiniciar", "action": "reiniciar"}
            ]}
        return {"response": response_text, "context": new_context, "data": response_data}

    # NUEVO: Manejo específico para prerrequisitos una vez que se pidió un curso
    if current_step == 'awaiting_course_for_info_prereq':
        course_code = find_course_by_keyword(user_message_normalized)
        if course_code:
            course_requirements = courses_db[course_code]['requirements']
            response_text = f"Los prerrequisitos para **{courses_db[course_code]['name']}** son: {course_requirements}.\n\n¿Hay algo más en lo que pueda ayudarte con este curso o necesitas ver otra cosa?"
            new_context['step'] = 'course_info_provided' # Volver al estado general de info de curso
            response_data = {"type": "action_buttons", "buttons": [
                {"text": f"Inscribirme en {courses_db[course_code]['name']}", "action": f"inscribirme_curso_{course_code}"},
                {"text": "Ver otros cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Menú principal", "action": "menu principal"}
            ]}
        else:
            response_text = "No logré identificar el curso. Por favor, dime el nombre exacto o el código del curso para darte sus prerrequisitos."
            # Se mantiene en 'awaiting_course_for_info_prereq'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Inglés para Principiantes A1", "action": "info_curso_ENG101"},
                {"text": "Introducción a Python", "action": "info_curso_PROG201"},
                {"text": "Cancelar", "action": "cancelar"}
            ]}
        return {"response": response_text, "context": new_context, "data": response_data}


    # --- Intenciones Primarias (sin un paso específico previo) ---
    # Prioridad: Human > Inscripción > FAQ > Cursos

    # Intención: Transferencia a Agente Humano
    if "humano" in user_message_normalized or "asesor" in user_message_normalized or "soporte" in user_message_normalized or "ayuda personalizada" in user_message_normalized:
        response_text = (
            "🤝 Entiendo. Para una atención más personalizada, por favor, déjame tu **nombre completo, email y número de teléfono** "
            "(con código de área) en un solo mensaje para que un asesor de admisiones pueda contactarte.\n\n"
            "Ejemplo: 'Soy Ana García, mi email es ana@ejemplo.com y mi teléfono es +5491112345678'."
        )
        new_context['step'] = 'collect_contact_for_human'
        new_context['contact_info'] = {} # Asegurar inicialización
        response_data = {"type": "action_buttons", "buttons": [
            {"text": "Soy [Tu Nombre], [Tu Email], [Tu Teléfono]", "action": "Soy Ana García, ana@ejemplo.com, +5491112345678"},
            {"text": "Cancelar", "action": "cancelar"}
        ]}
        return {"response": response_text, "context": new_context, "data": response_data}

    # Intención: Inscripción (cuando el usuario escribe la intención, no usa el botón específico)
    elif "inscribir" in user_message_normalized or "matricular" in user_message_normalized or "apuntarme" in user_message_normalized or "quiero entrar" in user_message_normalized:
        course_code = find_course_by_keyword(user_message_normalized)
        if course_code:
            new_context['step'] = 'awaiting_enrollment_name'
            new_context['last_queried_course_code'] = course_code
            response_text = f"¡Excelente! Para inscribirte en **{courses_db[course_code]['name']}**, por favor, dime tu nombre completo."
        else:
            response_text = "Para iniciar tu inscripción, ¿en qué curso te gustaría matricularte? Puedes decir el nombre completo o el código del curso."
            new_context['step'] = 'awaiting_course_for_enrollment'
            response_data = {"type": "action_buttons", "buttons": [
                {"text": "Inglés para Principiantes A1", "action": "inscribirme_curso_ENG101"},
                {"text": "Introducción a Python", "action": "inscribirme_curso_PROG201"},
                {"text": "Marketing Digital Avanzado", "action": "inscribirme_curso_MKT301"},
                {"text": "Ver todos los cursos", "action": "cursos"},
                {"text": "Cancelar", "action": "cancelar"}
            ]}
        return {"response": response_text, "context": new_context, "data": response_data}


    # Intención: Preguntas Frecuentes de Estudiantes
    elif ("preguntas frecuentes" in user_message_normalized or "faqs" in user_message_normalized or "dudas" in user_message_normalized or "informacion general" in user_message_normalized):
        response_text = (
            "📄 ¡Claro! Estoy aquí para ayudarte con nuestras **Preguntas Frecuentes**.\n"
            "¿Sobre qué tema te gustaría saber más?\n"
            "• **Horarios**\n"
            "• **Pagos**\n"
            "• **Profesores**\n"
            "• **Plataformas**\n"
            "• **Materiales**\n"
            "• **Reglamentos**\n"
            "• **Inscripción**\n"
            "• **Certificaciones**\n"
            "• **Prerrequisitos**\n\n"
            "Puedes hacer clic en un botón o escribir tu pregunta."
        )
        new_context['step'] = 'awaiting_edu_faq_topic'
        response_data = {"type": "action_buttons", "buttons": [
            {"text": "Horarios", "action": "horarios"},
            {"text": "Pagos", "action": "pagos"},
            {"text": "Profesores", "action": "profesores"},
            {"text": "Plataformas", "action": "plataformas"},
            {"text": "Materiales", "action": "materiales"},
            {"text": "Reglamentos", "action": "reglamentos"},
            {"text": "Inscripción", "action": "inscripcion"},
            {"text": "Certificaciones", "action": "certificaciones"},
            {"text": "Prerrequisitos", "action": "prerrequisitos"},
            {"text": "Cancelar", "action": "cancelar"}
        ]}
        return {"response": response_text, "context": new_context, "data": response_data}


    # Intención: Información de Cursos y Programas (incluye "detalles de", "informacion sobre", "curriculum", "precio", "ver mas")
    elif "cursos" in user_message_normalized or "programas" in user_message_normalized or "oferta educativa" in user_message_normalized or "que enseñan" in user_message_normalized or "detalles de" in user_message_normalized or "informacion sobre" in user_message_normalized or "curriculum" in user_message_normalized or "precio" in user_message_normalized or "ver mas" in user_message_normalized:
        course_code = find_course_by_keyword(user_message_normalized)
        if course_code:
            response_text = "Aquí tienes la información detallada que solicitaste:"
            response_data = get_course_details_response_data(course_code)
            new_context['step'] = 'course_info_provided'
            # Botones mejorados después de mostrar una tarjeta de curso
            response_data['buttons'] = [
                {"text": f"Inscribirme en {courses_db[course_code]['name']}", "action": f"inscribirme_curso_{course_code}"},
                {"text": "Ver otros cursos", "action": "cursos"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Menú principal", "action": "menu principal"}
            ]
        else:
            courses_list_simple = []
            for code, course_info in courses_db.items():
                courses_list_simple.append({
                    "name": course_info["name"],
                    "code": code,
                    "duration": course_info["duration"]
                })
            
            response_text = "🎓 ¡Claro! Aquí te presento algunos de nuestros cursos principales. Si te interesa alguno, menciona su nombre o código para ver todos los detalles:"
            response_data = {"type": "simple_course_list", "courses": courses_list_simple}
            # Botones para la lista de cursos
            response_data['buttons'] = [
                {"text": "Detalles de Inglés A1", "action": "info_curso_ENG101"},
                {"text": "Detalles de Python", "action": "info_curso_PROG201"},
                {"text": "Detalles de Marketing Digital", "action": "info_curso_MKT301"},
                {"text": "Inscribirme en un curso", "action": "inscribirme"},
                {"text": "Menú principal", "action": "menu principal"}
            ]
            new_context['step'] = 'course_list_provided'
        return {"response": response_text, "context": new_context, "data": response_data}

    # Intención: Despedida / Agradecimiento
    elif "gracias" in user_message_normalized or "chau" in user_message_normalized or "adios" in user_message_normalized or "bye" in user_message_normalized:
        response_text = "😊 ¡De nada! Fue un placer ayudarte. Si tienes más preguntas, no dudes en consultarme. ¡Que tengas un excelente día de estudio!"
        new_context['step'] = 'goodbye'
        response_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver Cursos", "action": "cursos"},
            {"text": "Inscribirme", "action": "inscribirme"},
            {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"},
            {"text": "Reiniciar", "action": "reiniciar"}
        ]}
        return {"response": response_text, "context": new_context, "data": response_data}


    # --- Fallback (Si ninguna intención fue reconocida) ---
    response_text = (
        "😕 Disculpa, no logré entender tu consulta. Soy **Edubot**, tu Agente Educativo Automatizado. "
        "Mis funciones principales son:\n"
        "• **Información de cursos:** (ej. 'cursos', 'detalles de Inglés A1')\n"
        "• **Proceso de inscripción:** (ej. 'quiero inscribirme', 'matricularme en Python')\n"
        "• **Preguntas frecuentes:** (ej. 'preguntas frecuentes', 'horarios de cursos', 'métodos de pago')\n"
        "• **Conectarte con un asesor:** (ej. 'hablar con un humano')\n\n"
        "¿En qué te puedo asistir específicamente?"
    )
    new_context['step'] = 'main_menu'
    response_data = {"type": "action_buttons", "buttons": [
        {"text": "Ver Cursos", "action": "cursos"},
        {"text": "Inscribirme", "action": "inscribirme"},
        {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
        {"text": "Hablar con un asesor", "action": "hablar con un asesor"}
    ]}
    return {"response": response_text, "context": new_context, "data": response_data}


# --- Rutas de la API de Flask ---

@app.route('/api/edubot_chat', methods=['POST'])
def edubot_chat_webhook():
    try:
        user_input = request.json.get('message', '')
        user_id = request.json.get('user_id', 'web_user_default')

        context = conversation_contexts.get(user_id, {
            "step": "welcome",
            "last_queried_course_code": None,
            "contact_info": {}
        })
        
        print(f"DEBUG_WEBHOOK: Mensaje recibido: '{user_input}', Contexto inicial: {context}")

        result = handle_edubot_message(user_input, context)
        
        conversation_contexts[user_id] = result["context"]
        
        print(f"DEBUG_WEBHOOK: Respondiendo: '{result['response']}', Contexto actualizado: {result['context']}, Datos: {result['data']}")

        return jsonify(result)

    except Exception as e:
        print(f"ERROR_WEBHOOK: Error en edubot_chat_webhook: {e}", file=sys.stderr)
        return jsonify({
            "response": "Lo siento, hubo un error técnico inesperado en el servidor. Por favor, intenta de nuevo.",
            "context": {"step": "main_menu", "last_queried_course_code": None, "contact_info": {}},
            "data": {"type": "action_buttons", "buttons": [
                {"text": "Ver Cursos", "action": "cursos"},
                {"text": "Inscribirme", "action": "inscribirme"},
                {"text": "Preguntas Frecuentes", "action": "preguntas frecuentes"},
                {"text": "Hablar con un asesor", "action": "hablar con un asesor"}
            ]}
        }), 500


# Ruta de prueba para verificar que el servidor está corriendo
@app.route('/')
def home():
    return "EduBot (core) is running! Use /api/edubot_chat for web interactions. Other channels use their specific connectors."

# Inicia el servidor Flask en el puerto 5005.
if __name__ == '__main__':
    app.run(debug=True, port=5005)