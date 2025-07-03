import os
import re
import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from collections import defaultdict
import uuid

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Configura una clave secreta para las sesiones (cambia esto en producción)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_super_secret_key_healthbot_123')
CORS(app, supports_credentials=True) # Habilita CORS para todas las rutas

# --- Simulación de Base de Datos / Conocimiento ---

# Estructura de servicios médicos
HEALTH_SERVICES = {
    "clinica_medica": {
        "name": "Consulta de Clínica Médica",
        "description": "Atención integral para adultos, diagnóstico y tratamiento de enfermedades comunes.",
        "long_description": "La consulta de Clínica Médica se enfoca en la prevención, diagnóstico y tratamiento de enfermedades no quirúrgicas que afectan a los adultos. Incluye chequeos generales, manejo de enfermedades crónicas como hipertensión y diabetes, y atención de patologías agudas. Nuestro equipo de clínicos altamente capacitados está listo para brindarle una atención personalizada y de calidad.",
        "price": 3500.00,
        "duration_minutes": 30,
        "specialty": "Clínica Médica",
        "doctors": ["Dra. Ana García", "Dr. Luis Pérez"]
    },
    "odontologia": {
        "name": "Consulta Odontológica General",
        "description": "Revisión bucal completa, limpieza y diagnóstico de problemas dentales.",
        "long_description": "La consulta odontológica general incluye un examen exhaustivo de su salud bucal, detección de caries, evaluación de encías y huesos, y una limpieza dental profesional para eliminar placa y sarro. Es el primer paso fundamental para mantener una sonrisa sana y prevenir futuras complicaciones. ¡Visítenos para un control preventivo!",
        "price": 4200.00,
        "duration_minutes": 45,
        "specialty": "Odontología",
        "doctors": ["Dra. Sofía Rodríguez", "Dr. Javier López"]
    },
    "dermatologia": {
        "name": "Consulta Dermatológica",
        "description": "Diagnóstico y tratamiento de afecciones de la piel, cabello y uñas.",
        "long_description": "Nuestros dermatólogos están especializados en el diagnóstico y tratamiento de diversas afecciones dermatológicas, incluyendo acné, rosácea, dermatitis, lunares y enfermedades del cabello y las uñas. Ofrecemos tratamientos personalizados y asesoramiento para el cuidado de su piel. Su bienestar y salud cutánea son nuestra prioridad.",
        "price": 5000.00,
        "duration_minutes": 30,
        "specialty": "Dermatología",
        "doctors": ["Dra. Valeria Castro", "Dr. Marcos Giménez"]
    },
    "pediatria": {
        "name": "Consulta Pediátrica",
        "description": "Atención médica integral para niños y adolescentes, seguimiento de desarrollo y vacunas.",
        "long_description": "La consulta pediátrica brinda atención médica especializada a bebés, niños y adolescentes. Nos enfocamos en el crecimiento y desarrollo saludable, la prevención de enfermedades, la vacunación y el tratamiento de afecciones pediátricas comunes. Creemos en una atención cercana y de confianza para el bienestar de sus hijos.",
        "price": 4000.00,
        "duration_minutes": 40,
        "specialty": "Pediatría",
        "doctors": ["Dra. Laura Benítez", "Dr. Carlos Sosa"]
    },
    "cardiologia": {
        "name": "Consulta de Cardiología",
        "description": "Evaluación de la salud cardiovascular, diagnóstico y tratamiento de enfermedades del corazón.",
        "long_description": "La consulta de cardiología se dedica al estudio, diagnóstico y tratamiento de las enfermedades del corazón y del sistema circulatorio. Ofrecemos chequeos preventivos, evaluación de síntomas como dolor de pecho o palpitaciones, y manejo de condiciones como hipertensión arterial y arritmias. Su salud cardíaca es fundamental para nosotros.",
        "price": 6000.00,
        "duration_minutes": 45,
        "specialty": "Cardiología",
        "doctors": ["Dr. Ricardo Silva"]
    },
    "nutricion": {
        "name": "Consulta de Nutrición",
        "description": "Asesoramiento nutricional personalizado para una dieta saludable y manejo de peso.",
        "long_description": "Nuestros nutricionistas brindan planes de alimentación personalizados para diversas necesidades: pérdida de peso, control de enfermedades crónicas, nutrición deportiva o simplemente mejorar sus hábitos alimenticios. Recibirá un acompañamiento constante para alcanzar sus objetivos de salud y bienestar de forma sostenible.",
        "price": 3800.00,
        "duration_minutes": 60,
        "specialty": "Nutrición",
        "doctors": ["Lic. María Paz"]
    }
}

# Simulación de turnos agendados para doctores específicos
# Key: (doctor_name, date_str): List of booked times (HH:MM)
BOOKED_SLOTS = defaultdict(list)
# BOOKINGS_DB: {booking_id: {service_code, doctor, date, time, patient_info, status, original_booking_date, original_booking_time}}
BOOKINGS_DB = {}

# ID inicial para las reservas de HealthBot
NEXT_BOOKING_ID = 1000

# Horarios de atención (general para todos los doctores por simplicidad)
AVAILABLE_HOURS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30"
]

# --- Funciones de Utilidad ---

def get_next_booking_id():
    """Genera un ID de reserva único."""
    global NEXT_BOOKING_ID
    booking_id = f"HLT-{NEXT_BOOKING_ID}"
    NEXT_BOOKING_ID += 1
    return booking_id

def parse_date(text):
    """Intenta parsear una fecha desde el texto (hoy, mañana, dd-mm-yyyy)."""
    text_lower = text.lower()
    today = datetime.date.today()

    if "hoy" in text_lower:
        return today
    elif "mañana" in text_lower or "manana" in text_lower:
        return today + datetime.timedelta(days=1)
    elif "pasado mañana" in text_lower or "pasado manana" in text_lower:
        return today + datetime.timedelta(days=2)
    else:
        # Intentar parsear formatos dd-mm-yyyy o dd/mm/yyyy
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
        if match:
            try:
                day, month, year = map(int, match.groups())
                date_obj = datetime.date(year, month, day)
                # Opcional: Validar que la fecha no sea en el pasado
                if date_obj < today:
                    return None # Fecha en el pasado no válida
                return date_obj
            except ValueError:
                return None
    return None

def parse_time(text):
    """Intenta parsear una hora desde el texto (HH:MM)."""
    match = re.search(r'(\d{1,2})[.:](\d{2})', text)
    if match:
        try:
            hour, minute = map(int, match.groups())
            if 0 <= hour < 24 and 0 <= minute < 60:
                return f"{hour:02d}:{minute:02d}"
            return None
        except ValueError:
            return None
    return None

def find_service_by_name_or_code(query):
    """Busca un servicio por nombre (parcial) o código."""
    query_lower = query.lower()
    for code, service in HEALTH_SERVICES.items():
        if code == query_lower or query_lower in service["name"].lower() or query_lower == service["specialty"].lower():
            return code, service
    return None, None

def get_available_slots(doctor_name, date_obj, service_duration_minutes):
    """
    Calcula los slots disponibles para un doctor y fecha, considerando la duración del servicio.
    Esto es una simulación simplificada.
    """
    date_str = date_obj.strftime("%Y-%m-%d")
    booked_times = BOOKED_SLOTS[(doctor_name, date_str)]
    available_slots = []

    # Convertir duración del servicio a minutos para comparación
    duration_delta = datetime.timedelta(minutes=service_duration_minutes)

    for start_time_str in AVAILABLE_HOURS:
        start_dt = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        
        # Crear un datetime object para la fecha y hora de inicio propuesta
        proposed_start_datetime = datetime.datetime.combine(date_obj, start_dt)
        proposed_end_datetime = proposed_start_datetime + duration_delta

        is_slot_booked = False
        for booked_time_str in booked_times:
            # Simplemente verificaremos si el inicio de la ranura propuesta coincide con una hora reservada
            # Esto es simplista; una implementación real requeriría verificar solapamientos de rangos de tiempo.
            if start_time_str == booked_time_str:
                is_slot_booked = True
                break
        
        if not is_slot_booked:
            available_slots.append(start_time_str)
            
    return available_slots

# --- Lógica del Bot ---

async def get_bot_response(message, context):
    """
    Procesa el mensaje del usuario y genera la respuesta del bot.
    Adapta esta función para el HealthBot.
    """
    user_message = message.lower().strip()
    
    # Inicializar o recuperar el estado de la sesión
    session_state = context if context else {}
    session_state.setdefault('step', 'welcome')
    session_state.setdefault('selected_service_code', None)
    session_state.setdefault('selected_doctor', None)
    session_state.setdefault('booking_details', {})
    session_state.setdefault('patient_info', {
        'prepaga': None,
        'name': None,
        'phone': None,
        'email': None
    })
    session_state.setdefault('booking_id_for_action', None)
    session_state.setdefault('current_action', None) # 'agendar', 'reagendar', 'cancelar'


    response_text = "Disculpa, no te entendí. ¿Podrías repetirlo o elegir una opción del menú?"
    data = None # Para enviar datos estructurados al frontend

    # --- Manejo del saludo inicial y reinicio (Prioridad Máxima) ---
    if user_message == "hola" or user_message == "reiniciar":
        session_state = { # Resetear todo el estado
            'step': 'main_menu', # Pasa directamente a main_menu después del saludo inicial
            'selected_service_code': None,
            'selected_doctor': None,
            'booking_details': {},
            'patient_info': { 'prepaga': None, 'name': None, 'phone': None, 'email': None },
            'booking_id_for_action': None,
            'current_action': None
        }
        response_text = "¡Hola! Soy HealthBot, tu asistente para agendar citas médicas. ¿En qué puedo ayudarte hoy?"
        session['healthbot_state'] = session_state
        return response_text, session_state, data

    # --- Manejo de comandos principales (Alta Prioridad, antes de la lógica de steps) ---
    # Esto asegura que estos comandos se procesen siempre, sin importar el paso actual,
    # y reinician el flujo o dirigen a la acción correcta.
    if user_message == "agendar cita":
        response_text = "¿Qué tipo de consulta médica te gustaría agendar? Puedes decirme la especialidad o el nombre del servicio (ej. 'Clínica Médica', 'Dermatología')."
        session_state['step'] = 'awaiting_service_for_booking'
        session_state['current_action'] = 'agendar'
        # Limpiar cualquier estado previo de agendamiento/reagendamiento
        session_state['selected_service_code'] = None
        session_state['selected_doctor'] = None
        session_state['booking_details'] = {}
        session_state['patient_info'] = { 'prepaga': None, 'name': None, 'phone': None, 'email': None }
        session['healthbot_state'] = session_state
        return response_text, session_state, data

    elif user_message == "reagendar cita":
        response_text = "Para reagendar tu cita, por favor, ingresa el ID de tu reserva (ej. HLT-1234)."
        session_state['step'] = 'awaiting_booking_id_for_action'
        session_state['current_action'] = 'reagendar'
        # Limpiar cualquier estado de agendamiento previo
        session_state['selected_service_code'] = None
        session_state['selected_doctor'] = None
        session_state['booking_details'] = {}
        session_state['patient_info'] = { 'prepaga': None, 'name': None, 'phone': None, 'email': None }
        session['healthbot_state'] = session_state
        return response_text, session_state, data
    
    elif user_message == "cancelar cita":
        response_text = "Para cancelar tu cita, por favor, ingresa el ID de tu reserva (ej. HLT-1234)."
        session_state['step'] = 'awaiting_booking_id_for_action'
        session_state['current_action'] = 'cancelar'
        # Limpiar cualquier estado de agendamiento previo
        session_state['selected_service_code'] = None
        session_state['selected_doctor'] = None
        session_state['booking_details'] = {}
        session_state['patient_info'] = { 'prepaga': None, 'name': None, 'phone': None, 'email': None }
        session['healthbot_state'] = session_state
        return response_text, session_state, data

    elif "servicios" in user_message or "ver servicios" in user_message:
        response_text = "Claro, estos son nuestros servicios médicos principales:"
        data = {
            "type": "simple_service_list",
            "services": [
                {"name": s["name"], "code": code, "price": s["price"]}
                for code, s in HEALTH_SERVICES.items()
            ]
        }
        session_state['step'] = 'service_list_provided'
        session_state['current_action'] = None # Asegurar que no hay acción pendiente
        session['healthbot_state'] = session_state
        return response_text, session_state, data

    elif "hablar con un asesor" in user_message or "asesor" in user_message:
        response_text = "Entiendo. Por favor, indícame tu nombre completo y número de teléfono para que un asesor se ponga en contacto contigo."
        session_state['step'] = 'collect_contact_for_human_healthbot'
        session_state['current_action'] = None # Asegurar que no hay acción pendiente
        session['healthbot_state'] = session_state
        return response_text, session_state, data
    
    elif "cancelar" in user_message:
        # Este es el 'cancelar' general, diferente al 'cancelar cita' que pide ID
        # Se activa si el usuario dice "cancelar" en un flujo intermedio.
        # No se activa si estamos en confirm_cancelation porque los botones tienen acciones específicas.
        if session_state['step'] not in ['welcome', 'confirm_cancelation', 'main_menu']: # No resetear si ya estamos en un estado final o esperando confirmación de cancelación
            session_state = { # Resetear todo el estado
                'step': 'main_menu',
                'selected_service_code': None,
                'selected_doctor': None,
                'booking_details': {},
                'patient_info': { 'prepaga': None, 'name': None, 'phone': None, 'email': None },
                'booking_id_for_action': None,
                'current_action': None
            }
            response_text = "De acuerdo, he cancelado la operación actual. ¿Hay algo más en lo que pueda ayudarte?"
            session['healthbot_state'] = session_state
            return response_text, session_state, data
        
    elif "menu principal" in user_message:
        session_state['step'] = 'main_menu'
        session_state['current_action'] = None # Asegurar que no hay acción pendiente
        response_text = "¿En qué más puedo ayudarte?"
        session['healthbot_state'] = session_state
        return response_text, session_state, data


    # --- Lógica basada en el paso actual (session_state['step']) ---

    if session_state['step'] == 'main_menu':
        response_text = "No estoy seguro de cómo ayudarte con eso. Puedes 'ver servicios', 'agendar una cita', 'reagendar cita', 'cancelar cita' o 'hablar con un asesor'."
        
    elif session_state['step'] == 'service_list_provided':
        if user_message.startswith("ver_servicio_"):
            service_code = user_message.replace("ver_servicio_", "")
            selected_service = HEALTH_SERVICES.get(service_code)
            if selected_service:
                # Asegurarse de que el doctor se muestre correctamente, tomando el primero de la lista
                doctor_name_for_display = selected_service['doctors'][0] if selected_service['doctors'] else "Doctor(a) General"
                
                response_text = f"Aquí tienes los detalles de **{selected_service['name']}**:"
                data = {
                    "type": "service_card",
                    "code": service_code,
                    "name": selected_service['name'],
                    "description": selected_service['description'],
                    "specialty": selected_service['specialty'],
                    "doctor": doctor_name_for_display, # Usa el primer doctor para mostrar
                    "duration_minutes": selected_service['duration_minutes'],
                    "price": selected_service['price']
                }
                session_state['selected_service_code'] = service_code
                session_state['step'] = 'service_info_provided'
            else:
                response_text = "Lo siento, no encontré detalles para ese servicio. Por favor, elige uno de la lista o escribe 'servicios' para verlos de nuevo."
                session_state['step'] = 'main_menu' # Volver al menú si hay un error
        else:
             response_text = "Si quieres ver más detalles de un servicio, haz clic en 'Ver detalles'. Si quieres agendar, dime qué servicio."
             data = {
                "type": "simple_service_list",
                "services": [
                    {"name": s["name"], "code": code, "price": s["price"]}
                    for code, s in HEALTH_SERVICES.items()
                ]
            }

    elif session_state['step'] == 'service_info_provided':
        if user_message.startswith("agendar_servicio_"):
            service_code = user_message.replace("agendar_servicio_", "")
            selected_service = HEALTH_SERVICES.get(service_code)
            if selected_service:
                session_state['selected_service_code'] = service_code
                # Seleccionar el primer doctor de la lista para este servicio
                session_state['selected_doctor'] = selected_service['doctors'][0] if selected_service['doctors'] else "Doctor(a) General"
                response_text = f"Excelente, quieres agendar **{selected_service['name']}**. ¿Qué día te gustaría agendar tu cita? Puedes decir 'hoy', 'mañana' o una fecha (ej. {datetime.date.today().day + 1}-{datetime.date.today().month}-{datetime.date.today().year})."
                session_state['step'] = 'awaiting_booking_date'
                session_state['current_action'] = 'agendar'
            else:
                response_text = "Lo siento, no pude identificar ese servicio. Por favor, intenta de nuevo o escribe 'servicios' para ver la lista."
                session_state['step'] = 'main_menu'
        elif user_message.startswith("mas_informacion_"):
            service_code = user_message.replace("mas_informacion_", "")
            selected_service = HEALTH_SERVICES.get(service_code)
            if selected_service and selected_service.get("long_description"):
                response_text = "Aquí tienes más información detallada:"
                data = {
                    "type": "text_with_action",
                    "response_text": selected_service["long_description"],
                    "service_code": service_code # Para que el botón de agendar funcione
                }
                session_state['step'] = 'service_long_info_provided'
            else:
                response_text = "No hay más información detallada disponible para este servicio en este momento."
                session_state['step'] = 'service_info_provided' # Mantener en el mismo paso
        else:
            response_text = "Para agendar, haz clic en 'Agendar este servicio'. Si no, puedo mostrarte otros 'servicios'."

    elif session_state['step'] == 'service_long_info_provided':
        if user_message.startswith("agendar_servicio_"):
            service_code = user_message.replace("agendar_servicio_", "")
            selected_service = HEALTH_SERVICES.get(service_code)
            if selected_service:
                session_state['selected_service_code'] = service_code
                session_state['selected_doctor'] = selected_service['doctors'][0] if selected_service['doctors'] else "Doctor(a) General"
                response_text = f"Excelente, quieres agendar **{selected_service['name']}**. ¿Qué día te gustaría agendar tu cita? Puedes decir 'hoy', 'mañana' o una fecha (ej. {datetime.date.today().day + 1}-{datetime.date.today().month}-{datetime.date.today().year})."
                session_state['step'] = 'awaiting_booking_date'
                session_state['current_action'] = 'agendar'
            else:
                response_text = "Lo siento, no pude identificar ese servicio para agendar. Por favor, intenta de nuevo."
                session_state['step'] = 'main_menu'
        else:
            response_text = "¿Hay algo más en lo que pueda ayudarte? Puedes 'agendar una cita' o 'ver servicios'."
            session_state['step'] = 'main_menu' # Vuelve al menú principal si no agenda

    elif session_state['step'] == 'awaiting_service_for_booking':
        # Esta es la parte donde el usuario escribe el nombre del servicio (ej. "Dermatología")
        service_code, selected_service = find_service_by_name_or_code(user_message)
        if selected_service:
            session_state['selected_service_code'] = service_code
            session_state['selected_doctor'] = selected_service['doctors'][0] if selected_service['doctors'] else "Doctor(a) General"
            response_text = f"Has elegido **{selected_service['name']}** con la especialidad de **{selected_service['specialty']}**. ¿Qué día te gustaría agendar tu cita? Puedes decir 'hoy', 'mañana' o una fecha (ej. {datetime.date.today().day + 1}-{datetime.date.today().month}-{datetime.date.today().year})."
            session_state['step'] = 'awaiting_booking_date'
        else:
            response_text = "Lo siento, no encuentro esa especialidad o servicio. Por favor, intenta con otro nombre (ej. 'Clínica Médica', 'Odontología') o escribe 'servicios' para ver la lista completa."
            # Mantiene el paso para que el usuario pueda reintentar
            session_state['step'] = 'awaiting_service_for_booking'


    elif session_state['step'] in ['awaiting_booking_date', 'awaiting_reschedule_date']:
        date_obj = parse_date(user_message)
        if date_obj:
            # Asegurarse de que booking_details exista para evitar KeyError
            session_state['booking_details'] = session_state.get('booking_details', {}) 
            session_state['booking_details']['date'] = date_obj.strftime("%Y-%m-%d")
            
            selected_service = HEALTH_SERVICES.get(session_state['selected_service_code'])
            
            if not selected_service:
                response_text = "Hubo un error al recuperar los detalles del servicio. Por favor, intenta agendar de nuevo desde el inicio."
                session_state['step'] = 'main_menu'
                session_state['current_action'] = None # Limpiar acción
            else:
                # El doctor ya debería estar seleccionado en session_state['selected_doctor']
                selected_doctor = session_state['selected_doctor'] # Usar el doctor ya guardado
                if not selected_doctor: # Fallback por si acaso no se guardó bien
                     selected_doctor = selected_service['doctors'][0] if selected_service['doctors'] else "Doctor General"
                     session_state['selected_doctor'] = selected_doctor

                available_slots = get_available_slots(
                    selected_doctor, 
                    date_obj, 
                    selected_service['duration_minutes']
                )

                if available_slots:
                    response_text = f"Aquí tienes los horarios disponibles para **{selected_service['name']}** con **{selected_doctor}** el **{date_obj.strftime('%d/%m/%Y')}**:"
                    data = {
                        "type": "available_slots",
                        "date": session_state['booking_details']['date'],
                        "slots": available_slots
                    }
                    if session_state['current_action'] == 'agendar':
                        session_state['step'] = 'awaiting_booking_time'
                    elif session_state['current_action'] == 'reagendar':
                        session_state['step'] = 'awaiting_reschedule_time'
                else:
                    response_text = f"Lo siento, no hay horarios disponibles para **{selected_service['name']}** con **{selected_doctor}** el **{date_obj.strftime('%d/%m/%Y')}**. ¿Te gustaría intentar otra fecha?"
                    # No hay botones de acción aquí porque se espera que el usuario escriba una fecha.
                    # El frontend genera "Elegir otra fecha" o "Cancelar".
        else:
            response_text = "Esa no parece ser una fecha válida. Por favor, ingresa la fecha en formato día-mes-año (ej. {}-{}-{}) o di 'hoy'/'mañana'/'pasado mañana'.".format(
                datetime.date.today().day + 1, datetime.date.today().month, datetime.date.today().year)
            # Mantiene el paso para reintentar la fecha


    elif session_state['step'] in ['awaiting_booking_time', 'awaiting_reschedule_time']:
        # Solo procesamos si el mensaje es un slot_selected_ y estamos en el flujo correcto
        if user_message.startswith("slot_selected_"):
            parts = user_message.replace("slot_selected_", "").split('_')
            
            if len(parts) >= 2:
                selected_date_str = parts[0]
                selected_time_str_raw = parts[1]
                selected_time_str = selected_time_str_raw.replace('-', ':')
            else:
                response_text = "Hubo un problema al seleccionar la hora. Por favor, intenta de nuevo o elige otra fecha."
                session_state['step'] = 'awaiting_booking_date' if session_state['current_action'] == 'agendar' else 'awaiting_reschedule_date'
                session['healthbot_state'] = session_state
                return response_text, session_state, data

            time_obj = parse_time(selected_time_str)

            if time_obj and selected_date_str == session_state['booking_details'].get('date'):
                selected_service = HEALTH_SERVICES.get(session_state['selected_service_code'])
                if not selected_service:
                    response_text = "Hubo un error al recuperar los detalles del servicio. Por favor, intenta agendar de nuevo desde el inicio."
                    session_state['step'] = 'main_menu'
                    session_state['current_action'] = None
                    session['healthbot_state'] = session_state
                    return response_text, session_state, data
                
                doctor_name = session_state['selected_doctor']
                
                # Verificar si el slot ya está ocupado (simulación)
                if time_obj in BOOKED_SLOTS[(doctor_name, selected_date_str)]:
                    response_text = f"Lo siento, el horario {time_obj} ya no está disponible para {selected_service['name']} el {datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')}. Por favor, elige otro."
                    # Re-calcular y mostrar slots disponibles
                    available_slots = get_available_slots(
                        doctor_name, 
                        datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date(), 
                        selected_service['duration_minutes']
                    )
                    data = {
                        "type": "available_slots",
                        "date": session_state['booking_details']['date'],
                        "slots": available_slots
                    }
                    session['healthbot_state'] = session_state
                    return response_text, session_state, data

                # Lógica de AGENDAR (nueva cita)
                if session_state['current_action'] == 'agendar':
                    session_state['booking_details']['time'] = time_obj
                    response_text = f"Excelente, has seleccionado el horario para tu cita de **{selected_service['name']}** con **{doctor_name}** el **{selected_date_str}** a las **{time_obj}**."
                    response_text += "\n\nAhora, por favor, indícame el nombre de tu prepaga (ej. OSDE, Swiss Medical, o 'No tengo')."
                    session_state['step'] = 'awaiting_prepaga'
                    
                # Lógica de REAGENDAR (cita existente)
                elif session_state['current_action'] == 'reagendar': 
                    booking_id_to_reschedule = session_state['booking_id_for_action']
                    original_booking = BOOKINGS_DB.get(booking_id_to_reschedule)

                    if original_booking:
                        # Liberar el slot original de la cita que se está reagendando
                        original_date_str = original_booking['date']
                        original_time_str = original_booking['time']
                        original_doctor = original_booking['doctor']
                        
                        if original_time_str in BOOKED_SLOTS[(original_doctor, original_date_str)]:
                            BOOKED_SLOTS[(original_doctor, original_date_str)].remove(original_time_str)
                        
                        # Ocupar el nuevo slot
                        BOOKED_SLOTS[(doctor_name, selected_date_str)].append(time_obj)

                        # Actualizar la reserva en la "base de datos" simulada
                        original_booking['date'] = selected_date_str
                        original_booking['time'] = time_obj
                        original_booking['status'] = 'reagendado' # O 'confirmado'

                        response_text = f"¡Perfecto! Tu cita con ID **{booking_id_to_reschedule}** para **{selected_service['name']}** con **{doctor_name}** ha sido reagendada para el **{datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')}** a las **{time_obj}**."
                        session_state['step'] = 'booking_rescheduled'
                        # Limpiar los datos de la acción después de reagendar
                        session_state['booking_id_for_action'] = None
                        session_state['selected_service_code'] = None
                        session_state['selected_doctor'] = None
                        session_state['booking_details'] = {} 
                        session_state['patient_info'] = { 'prepaga': None, 'name': None, 'phone': None, 'email': None } 
                        session_state['current_action'] = None
                    else:
                        response_text = "Hubo un error al encontrar tu cita original para reagendar. Por favor, intenta de nuevo desde el inicio del proceso de reagendar."
                        session_state['step'] = 'main_menu'
                        session_state['current_action'] = None
                
            else:
                response_text = "Parece que la hora seleccionada no es válida o no corresponde a la fecha. Por favor, elige una de las opciones disponibles o intenta otra fecha."
                session_state['step'] = 'awaiting_booking_date' if session_state['current_action'] == 'agendar' else 'awaiting_reschedule_date'
        else: # Si el usuario no envía un slot_selected_ en este paso
            response_text = "Por favor, elige una de las horas disponibles haciendo clic en los botones, o si deseas, 'Elegir otra fecha'."
            # No cambiamos el paso, esperando que el usuario elija un botón o escriba una fecha.


    elif session_state['step'] == 'awaiting_prepaga':
        prepaga = user_message.title().strip()
        session_state['patient_info']['prepaga'] = prepaga
        response_text = "Gracias. Ahora, por favor, dime tu nombre completo."
        session_state['step'] = 'awaiting_patient_name'

    elif session_state['step'] == 'awaiting_patient_name':
        name = user_message.title().strip()
        if len(name) < 3: # Validacion simple
            response_text = "Ese nombre parece muy corto. Por favor, ingresa tu nombre completo."
        else:
            session_state['patient_info']['name'] = name
            response_text = f"De acuerdo, {name}. Ahora necesito tu número de teléfono (con código de área, ej. +5491112345678)."
            session_state['step'] = 'awaiting_patient_phone'

    elif session_state['step'] == 'awaiting_patient_phone':
        phone = user_message.strip()
        # Permite números con o sin '+', espacios o guiones, pero solo dígitos
        if re.fullmatch(r'^\+?\d[\d\s-]{6,14}\d$', phone): # Regex más flexible para teléfonos
            session_state['patient_info']['phone'] = phone.replace(" ", "").replace("-", "") # Limpiar antes de guardar
            response_text = "Gracias. Por último, ingresa tu dirección de correo electrónico."
            session_state['step'] = 'awaiting_patient_email'
        else:
            response_text = "Ese no parece ser un número de teléfono válido. Por favor, ingresa tu número con código de área (ej. +5491112345678)."

    elif session_state['step'] == 'awaiting_patient_email':
        email = user_message.strip()
        if re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
            session_state['patient_info']['email'] = email
            
            selected_service = HEALTH_SERVICES.get(session_state['selected_service_code'])
            booking_date = session_state['booking_details']['date']
            booking_time = session_state['booking_details']['time']
            doctor_name = session_state['selected_doctor']
            patient_name = session_state['patient_info']['name']
            patient_phone = session_state['patient_info']['phone']
            patient_email = session_state['patient_info']['email']
            patient_prepaga = session_state['patient_info']['prepaga']

            response_text = f"Por favor, revisa los datos de tu cita:\n" \
                            f"**Servicio:** {selected_service['name']} ({selected_service['specialty']})\n" \
                            f"**Doctor(a):** {doctor_name}\n" \
                            f"**Fecha:** {datetime.datetime.strptime(booking_date, '%Y-%m-%d').strftime('%d/%m/%Y')}\n" \
                            f"**Hora:** {booking_time}\n" \
                            f"**Paciente:** {patient_name}\n" \
                            f"**Prepaga:** {patient_prepaga}\n" \
                            f"**Teléfono:** {patient_phone}\n" \
                            f"**Email:** {patient_email}\n\n" \
                            "¿Confirmas estos datos para agendar tu cita?"
            
            # El frontend usa data.data.buttons para estos botones de acción
            data = {
                "type": "action_buttons",
                "buttons": [
                    {"text": "Confirmar cita", "action": "confirmar_cita"},
                    {"text": "Modificar datos", "action": "modificar_datos"},
                    {"text": "Cancelar", "action": "cancelar"}
                ]
            }
            session_state['step'] = 'confirm_booking_data'

        else:
            response_text = "Esa no parece ser una dirección de correo electrónico válida. Por favor, ingresa un email correcto."

    elif session_state['step'] == 'confirm_booking_data':
        if user_message == "confirmar_cita":
            booking_id = get_next_booking_id()
            
            # MARCAR EL SLOT COMO RESERVADO PERMANENTEMENTE AQUÍ
            booked_date = session_state['booking_details']['date']
            booked_time = session_state['booking_details']['time']
            booked_doctor = session_state['selected_doctor']
            BOOKED_SLOTS[(booked_doctor, booked_date)].append(booked_time)

            # Guardar la reserva
            BOOKINGS_DB[booking_id] = {
                "service_code": session_state['selected_service_code'],
                "doctor": session_state['selected_doctor'],
                "date": session_state['booking_details']['date'],
                "time": session_state['booking_details']['time'],
                "patient_info": session_state['patient_info'],
                "status": "confirmado",
                "booking_id": booking_id # Añadir el ID a la reserva misma
            }
            
            response_text = f"¡Excelente! Tu cita para **{HEALTH_SERVICES[session_state['selected_service_code']]['name']}** con **{session_state['selected_doctor']}** el **{datetime.datetime.strptime(session_state['booking_details']['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}** a las **{session_state['booking_details']['time']}** ha sido confirmada." \
                            f"\n\nTu número de reserva es: **{booking_id}**. Por favor, guárdalo." \
                            f"\n\nRecibirás un recordatorio por email en {session_state['patient_info']['email']}."
            session_state['step'] = 'booking_confirmed'
            # Limpiar datos temporales después de la confirmación
            session_state['selected_service_code'] = None
            session_state['selected_doctor'] = None
            session_state['booking_details'] = {}
            session_state['patient_info'] = { 'prepaga': None, 'name': None, 'phone': None, 'email': None }
            session_state['current_action'] = None

        elif user_message == "modificar_datos":
            response_text = "¿Qué dato deseas modificar? ¿La fecha, la hora, la prepaga, tu nombre, teléfono o email?"
            # Simplificamos volviendo a pedir la fecha como primer paso de modificación
            session_state['step'] = 'awaiting_booking_date' # Asumimos que modificar datos en agendamiento es como empezar de nuevo la selección de fecha
            response_text += "\n\nPara modificar tu cita, por favor, dime nuevamente la fecha que te gustaría."

        else: # Si el usuario escribe algo distinto o hace click en un botón no esperado
            response_text = "Por favor, elige 'Confirmar cita' para finalizar o 'Modificar datos' para corregirlos."
            data = { # Vuelve a mostrar los botones de confirmación
                "type": "action_buttons",
                "buttons": [
                    {"text": "Confirmar cita", "action": "confirmar_cita"},
                    {"text": "Modificar datos", "action": "modificar_datos"},
                    {"text": "Cancelar", "action": "cancelar"}
                ]
            }

    elif session_state['step'] == 'awaiting_booking_id_for_action':
        booking_id = user_message.upper().strip()
        booking = BOOKINGS_DB.get(booking_id)

        if booking and booking['status'] != 'cancelado':
            session_state['booking_id_for_action'] = booking_id # Guardar el ID para la acción
            
            if session_state['current_action'] == 'reagendar':
                # Al reagendar, necesitamos saber qué servicio es para pedir nueva fecha y hora
                session_state['selected_service_code'] = booking['service_code']
                session_state['selected_doctor'] = booking['doctor'] # Mantener el mismo doctor

                response_text = f"Encontré tu cita con ID **{booking_id}** para **{HEALTH_SERVICES[booking['service_code']]['name']}** el **{datetime.datetime.strptime(booking['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}** a las **{booking['time']}**. " \
                                f"¿Qué nueva fecha te gustaría para reagendarla?"
                session_state['step'] = 'awaiting_reschedule_date' # Ir a pedir nueva fecha
            elif session_state['current_action'] == 'cancelar':
                response_text = f"Encontré tu cita con ID **{booking_id}** para **{HEALTH_SERVICES[booking['service_code']]['name']}** el **{datetime.datetime.strptime(booking['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}** a las **{booking['time']}**. " \
                                f"¿Estás seguro(a) de que quieres cancelar esta cita?"
                data = { # Botones de confirmación de cancelación
                    "type": "action_buttons",
                    "buttons": [
                        {"text": "Sí, cancelar", "action": "confirm_cancelation"},
                        {"text": "No, mantener", "action": "no_cancelar"}
                    ]
                }
                session_state['step'] = 'confirm_cancelation' # Ir a pedir confirmación
            else: # Fallback si current_action no está definido (ej. usuario escribe solo el ID sin contexto)
                 response_text = "ID de reserva encontrado, pero no sé qué acción quieres realizar. ¿Reagendar o cancelar?"
                 data = {
                    "type": "action_buttons",
                    "buttons": [
                        {"text": "Reagendar", "action": "reagendar cita"}, # Envía el comando "reagendar cita"
                        {"text": "Cancelar", "action": "cancelar cita"} # Envía el comando "cancelar cita"
                    ]
                }
                 session_state['step'] = 'main_menu' # Vuelve al menú para elegir acción
        elif booking and booking['status'] == 'cancelado':
            response_text = f"La reserva con ID **{booking_id}** ya ha sido cancelada previamente."
            session_state['step'] = 'main_menu'
            session_state['current_action'] = None # Limpiar acción
        else:
            response_text = "Lo siento, no encontré una cita con ese ID o ya fue cancelada. Por favor, verifica el ID o elige otra opción."
            data = {
                "type": "action_buttons",
                "buttons": [
                    {"text": "Intentar de nuevo", "action": "reagendar cita" if session_state['current_action'] == 'reagendar' else 'cancelar cita'},
                    {"text": "Volver al menú principal", "action": "menu principal"}
                ]
            }
            
    elif session_state['step'] == 'confirm_cancelation':
        if user_message == "confirm_cancelation": # El botón "Sí, cancelar" envía este action
            booking_id = session_state['booking_id_for_action']
            if booking_id and BOOKINGS_DB.get(booking_id):
                # Liberar el slot (simulado)
                booked_date_str = BOOKINGS_DB[booking_id]['date']
                booked_time_str = BOOKINGS_DB[booking_id]['time']
                booked_doctor = BOOKINGS_DB[booking_id]['doctor']
                
                if booked_time_str in BOOKED_SLOTS[(booked_doctor, booked_date_str)]:
                    BOOKED_SLOTS[(booked_doctor, booked_date_str)].remove(booked_time_str)
                
                BOOKINGS_DB[booking_id]['status'] = 'cancelado' # Actualizar estado
                response_text = f"Tu cita con ID **{booking_id}** ha sido cancelada exitosamente."
                session_state['step'] = 'booking_cancelled'
                session_state['booking_id_for_action'] = None # Limpiar
                session_state['current_action'] = None # Limpiar acción
            else:
                response_text = "Hubo un error al cancelar la cita. Por favor, intenta de nuevo o contacta a un asesor."
                session_state['step'] = 'main_menu'
                session_state['current_action'] = None # Limpiar acción
        elif user_message == "no_cancelar": # El botón "No, mantener" envía este action
            response_text = "De acuerdo, tu cita no ha sido cancelada. ¿Hay algo más en lo que pueda ayudarte?"
            session_state['step'] = 'main_menu'
            session_state['booking_id_for_action'] = None # Limpiar
            session_state['current_action'] = None # Limpiar acción
        else: # Si el usuario escribe otra cosa en este paso
            response_text = "Por favor, utiliza los botones para confirmar o cancelar la operación."
            data = { # Vuelve a mostrar los botones de confirmación
                "type": "action_buttons",
                "buttons": [
                    {"text": "Sí, cancelar", "action": "confirm_cancelation"},
                    {"text": "No, mantener", "action": "no_cancelar"}
                ]
            }
        
    elif session_state['step'] == 'collect_contact_for_human_healthbot':
        name_match = re.search(r'(soy|mi nombre es)\s+(.+?)(?:,|$)', user_message, re.IGNORECASE)
        phone_match = re.search(r'(?:mi teléfono es|es)\s*(\+?\d[\d\s-]{7,})', user_message, re.IGNORECASE)

        collected_name = None
        collected_phone = None

        if name_match:
            collected_name = name_match.group(2).strip()
        if phone_match:
            collected_phone = phone_match.group(1).strip().replace(" ", "").replace("-", "")

        if collected_name and collected_phone:
            session_state['contact_info'] = {'name': collected_name, 'phone': collected_phone}
            response_text = f"Gracias, **{collected_name}**. Un asesor se pondrá en contacto contigo al **{collected_phone}** a la brevedad." \
                            f"\n\n¿Hay algo más en lo que pueda ayudarte hoy?"
            session_state['step'] = 'human_contact_collected'
            session_state['current_action'] = None # Limpiar acción
        else:
            response_text = "Necesito tu nombre completo y número de teléfono para que un asesor te contacte. Por favor, intenta de nuevo (ej. 'Soy Juan Pérez, mi teléfono es +5491112345678')."

    # --- Fallback Final: Si no se procesó nada, se muestra el mensaje predeterminado ---
    # Este else solo se ejecuta si NINGÚN `if` o `elif` anterior ha retornado.
    # Si la respuesta sigue siendo la inicial, significa que no se encontró una intención clara.
    # Se debe mantener este bloque al final, solo si response_text no ha sido modificado.
    if response_text == "Disculpa, no te entendí. ¿Podrías repetirlo o elegir una opción del menú?":
        response_text = "No estoy seguro de cómo ayudarte con eso. Puedes 'ver servicios', 'agendar una cita', 'reagendar cita', 'cancelar cita' o 'hablar con un asesor'."
        session_state['step'] = 'main_menu' # Asegura que volvemos a un estado conocido
        session_state['current_action'] = None # Limpiar acción
        
    session['healthbot_state'] = session_state # Guardar el estado actualizado

    return response_text, session_state, data

# --- Rutas Flask ---

@app.route('/api/healthbot_chat', methods=['POST'])
async def healthbot_chat():
    user_message = request.json.get('message')
    context = request.json.get('context')
    user_id = request.json.get('user_id', 'anon')

    # Reconstruir la sesión del usuario con el contexto enviado
    # Si el contexto es None (primera vez), se inicializará en get_bot_response
    session['healthbot_state'] = context 

    # Procesar el mensaje y obtener respuesta
    bot_response_text, new_context, response_data = await get_bot_response(user_message, session['healthbot_state'])

    return jsonify({
        'response': bot_response_text,
        'context': new_context,
        'data': response_data
    })

@app.route('/')
def serve_index():
    # Asegúrate de que el archivo HTML esté en la misma carpeta que app.py
    return app.send_static_file('index_healthbot.html')

if __name__ == '__main__':
    app.run(debug=True, port=5010)