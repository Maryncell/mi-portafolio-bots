# mi-portafolio-bots/agendabot/core/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
import re
import os
import sys

# La app de Flask se inicializa aquí
app = Flask(__name__)
CORS(app) # Habilitar CORS para permitir solicitudes desde el frontend web

# --- Base de Datos Simulada (AgendaBot) ---
services_db = {
    "corte_basico": {
        "code": "corte_basico",
        "name": "Corte de Cabello Básico",
        "price": 25.00,
        "duration_minutes": 30,
        "description": "Un corte de cabello estándar para hombre o mujer. Incluye lavado y peinado básico.",
        "long_description": "**Corte de Cabello Básico:** Este servicio está diseñado para un mantenimiento regular de tu estilo. Incluye una consulta rápida con tu estilista para asegurar que el resultado sea exactamente lo que buscas. Se lava, corta y peina el cabello. Ideal para quienes buscan un look fresco y ordenado sin complicaciones. Duración: 30 minutos. Precio: $25.00. Disponible de Lunes a Sábado."
    },
    "manicura_clasica": {
        "code": "manicura_clasica",
        "name": "Manicura Clásica",
        "price": 18.00,
        "duration_minutes": 45,
        "description": "Limpieza, limado, pulido y esmaltado de uñas con esmalte regular.",
        "long_description": "**Manicura Clásica:** Tus manos merecen lo mejor. Este servicio incluye un remojo suave para tus manos, arreglo de cutículas, limado y pulido de uñas para darles forma. Finalizamos con un esmaltado de tu color preferido de nuestra colección estándar. Tus manos lucirán impecables y cuidadas. Duración: 45 minutos. Precio: $18.00. Ideal para un retoque rápido o para mantener tus manos siempre perfectas."
    },
    "masaje_relajacion_60min": {
        "code": "masaje_relajacion_60min",
        "name": "Masaje de Relajación (60min)",
        "price": 60.00,
        "duration_minutes": 60,
        "description": "Masaje de cuerpo completo para aliviar el estrés y la tensión.",
        "long_description": "**Masaje de Relajación (60min):** Sumérgete en una hora de pura tranquilidad con nuestro masaje de relajación. Utilizando aceites esenciales suaves y técnicas de presión moderada, nuestros terapeutas expertos trabajarán para liberar la tensión muscular y promover una profunda sensación de calma. Este masaje está diseñado para reducir el estrés, mejorar la circulación y rejuvenecer tu mente y cuerpo. Te sentirás renovado y completamente relajado. Duración: 60 minutos. Precio: $60.00. No olvides avisar si tienes alguna condición especial."
    },
    "drenaje_linfatico": {
        "code": "drenaje_linfatico",
        "name": "Drenaje Linfático",
        "price": 75.00,
        "duration_minutes": 90,
        "description": "Masaje suave que ayuda a mover el líquido linfático, reduciendo la hinchazón y mejorando la circulación.",
        "long_description": "**Drenaje Linfático:** Este masaje terapéutico es una técnica suave y rítmica diseñada para estimular el sistema linfático. Ideal para reducir la hinchazón (edema), desintoxicar el cuerpo y mejorar la circulación. Es particularmente beneficioso después de cirugías, para personas con retención de líquidos o simplemente para mejorar el bienestar general y la respuesta inmune. Nuestros especialistas te guiarán a través de una experiencia relajante y beneficiosa para tu salud. Duración: 90 minutos. Precio: $75.00. Se recomienda una serie de sesiones para sesiones."
    }
}

# Un diccionario para almacenar las reservas (simuladas)
bookings_db = {}
# Variable global para el ID de reserva, para que sea secuencial y fácil de recordar
next_booking_num = 1000 

# --- Estado de la Conversación (simulado) ---
conversation_contexts = {}

# --- Funciones de Utilidad ---

def generate_booking_id():
    """Genera un ID de reserva único y secuencial para la demo."""
    global next_booking_num
    booking_id = f"AGB-{next_booking_num}"
    next_booking_num += 1
    return booking_id

def get_available_slots(service_code, date_str):
    if service_code not in services_db:
        return []

    try:
        requested_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return []

    slots = []
    service_duration = services_db[service_code]["duration_minutes"]
    
    start_time = datetime.time(9, 0)
    end_time = datetime.time(17, 0)

    current_slot_start = datetime.datetime.combine(requested_date, start_time)
    
    now = datetime.datetime.now()

    while current_slot_start.time() < end_time:
        slot_end_time = current_slot_start + datetime.timedelta(minutes=service_duration)

        if slot_end_time.time() > end_time or (slot_end_time.hour == end_time.hour and slot_end_time.minute > end_time.minute):
            break

        if requested_date == now.date() and current_slot_start < now:
            current_slot_start += datetime.timedelta(minutes=30)
            continue

        if current_slot_start.hour >= 13 and current_slot_start.hour < 14: # Simular hora de almuerzo
            current_slot_start = current_slot_start.replace(hour=14, minute=0)
            continue

        slots.append(current_slot_start.strftime("%H:%M"))
        current_slot_start += datetime.timedelta(minutes=30)

    return slots

def get_service_details(service_identifier):
    service_identifier_lower = service_identifier.lower()
    for code, details in services_db.items():
        if code == service_identifier_lower:
            return details
        if service_identifier_lower in details["name"].lower():
            return details
    return None

def format_service_list(services):
    if not services:
        return "No hay servicios disponibles en este momento."
    
    response_text = "Estos son nuestros servicios disponibles:"
    return {
        "response": response_text,
        "data": {
            "type": "simple_service_list",
            "services": [
                {"code": s["code"], "name": s["name"], "price": s["price"], "description": s["description"]}
                for s in services
            ]
        }
    }

def validate_date(date_str):
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj >= datetime.date.today():
            return date_obj
    except ValueError:
        pass
    return None

def validate_time(time_str):
    try:
        datetime.datetime.strptime(time_str, '%H:%M').time()
        return time_str
    except ValueError:
        pass
    return None

def validate_phone(phone_number):
    cleaned_number = re.sub(r'[^\d+]', '', phone_number)
    if re.fullmatch(r'^\+?\d{7,20}$', cleaned_number):
        return cleaned_number
    return None

# --- Lógica Principal del Bot (handle_agendabot_message) ---

def handle_agendabot_message(user_message, context):
    response_text = "Lo siento, no entendí tu solicitud. ¿Podrías intentar con 'servicios', 'agendar cita' o 'ayuda'?"
    return_data = None
    next_step = context.get('step', 'welcome')
    user_message_lower = user_message.lower().strip()

    # --- Manejo de Comandos Globales con Alta Prioridad ---
    if user_message_lower == "reiniciar" or user_message_lower == "menu principal":
        response_text = "¡Hola! Soy AgendaBot, tu asistente personal para agendar citas. ¿En qué puedo ayudarte hoy?"
        next_step = "main_menu" # Cambiado a main_menu para que renderSuggestions lo maneje
        return_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver servicios", "action": "servicios"},
            {"text": "Agendar una cita", "action": "agendar cita"},
            {"text": "Reagendar cita", "action": "reagendar cita"},
            {"text": "Cancelar cita", "action": "cancelar cita"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"}, # Añadido
            {"text": "Reiniciar", "action": "reiniciar"} # Añadido
        ]}
        # Asegurarse de que contact_info siempre es un dict al resetear el contexto
        context = {"step": next_step, "selected_service_code": None, "booking_details": {}, "contact_info": {}}
        return {"response": response_text, "context": context, "data": return_data}
    
    elif user_message_lower == "cancelar":
        response_text = "Operación cancelada. ¿Hay algo más en lo que pueda ayudarte?"
        next_step = "main_menu"
        context = {"step": next_step, "selected_service_code": None, "booking_details": {}, "contact_info": {}}
        return_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver servicios", "action": "servicios"},
            {"text": "Agendar una cita", "action": "agendar cita"},
            {"text": "Reagendar cita", "action": "reagendar cita"},
            {"text": "Cancelar cita", "action": "cancelar cita"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"}, # Añadido
            {"text": "Reiniciar", "action": "reiniciar"} # Añadido
        ]}
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower == "servicios":
        all_services = list(services_db.values())
        formatted_list_response = format_service_list(all_services)
        response_text = formatted_list_response["response"]
        return_data = formatted_list_response["data"]
        next_step = "service_list_provided"
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower == "agendar cita":
        response_text = "¿Qué servicio te gustaría agendar? Puedes decirme el nombre del servicio o elegir de la lista."
        next_step = "awaiting_service_for_booking"
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower.startswith("agendar_servicio_"):
        service_code = user_message_lower.replace("agendar_servicio_", "")
        service = get_service_details(service_code)
        if service:
            context['selected_service_code'] = service["code"]
            context['booking_details'] = {"service_code": service["code"]}
            response_text = f"Perfecto, has elegido **{service['name']}**. ¿Para qué fecha te gustaría agendar? (Formato AAAA-MM-DD, ej. 2025-07-30)"
            next_step = "awaiting_booking_date"
        else:
            response_text = "No pude encontrar ese servicio. Por favor, elige uno de la lista o escribe 'servicios' para verlos."
            next_step = "awaiting_service_for_booking"
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower.startswith("ver_servicio_"):
        service_code = user_message_lower.replace("ver_servicio_", "")
        service = get_service_details(service_code)
        if service:
            response_text = f"Aquí están los detalles de **{service['name']}**:\n\n" \
                            f"Precio: ${service['price']:.2f}\n" \
                            f"Duración estimada: {service['duration_minutes']} minutos\n\n" \
                            f"{service['description']}"
            return_data = {
                "type": "service_card",
                "code": service["code"],
                "name": service["name"],
                "price": service["price"],
                "duration_minutes": service["duration_minutes"],
                "description": service["description"]
            }
            next_step = "service_info_provided"
        else:
            response_text = "No pude encontrar los detalles de ese servicio."
            next_step = "service_list_provided"
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower.startswith("mas_informacion_"):
        service_code = user_message_lower.replace("mas_informacion_", "")
        service = get_service_details(service_code)
        if service and "long_description" in service:
            response_text = service["long_description"]
            return_data = {
                "type": "text_with_action",
                "response_text": service["long_description"],
                "service_code": service["code"]
            }
            next_step = "service_long_info_provided"
        else:
            response_text = "Lo siento, no hay más información detallada disponible para ese servicio en este momento."
            next_step = context.get('last_step', 'main_menu')
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower == "hablar con un asesor":
        response_text = "Claro, para conectarte con un asesor, por favor, déjame tu **nombre completo** y **número de teléfono** (incluyendo código de país, ej. +5491112345678)."
        next_step = "collect_contact_for_human_agendabot"
        context['action_type'] = 'human_contact'
        # Asegurarse de que contact_info siempre es un dict al resetear el contexto
        if 'contact_info' not in context or not isinstance(context['contact_info'], dict):
            context['contact_info'] = {}
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower == "reagendar cita":
        response_text = "Para reagendar, necesito el ID de tu reserva actual. ¿Podrías proporcionármelo? (Ej. AGB-1000)"
        next_step = "awaiting_booking_id_for_action"
        context['action_type'] = 'reschedule'
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    elif user_message_lower == "cancelar cita":
        response_text = "Para cancelar, necesito el ID de tu reserva. ¿Podrías proporcionármelo? (Ej. AGB-1000)"
        next_step = "awaiting_booking_id_for_action"
        context['action_type'] = 'cancel'
        context['step'] = next_step
        return {"response": response_text, "context": context, "data": return_data}

    # --- Lógica de Pasos Conversacionales (State Machine) ---
    # Estos pasos se ejecutan si ningún comando global de alta prioridad fue activado.

    if next_step == "welcome":
        response_text = "¡Hola! Soy AgendaBot, tu asistente personal para agendar citas. ¿En qué puedo ayudarte hoy?"
        next_step = "main_menu"
        return_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver servicios", "action": "servicios"},
            {"text": "Agendar una cita", "action": "agendar cita"},
            {"text": "Reagendar cita", "action": "reagendar cita"},
            {"text": "Cancelar cita", "action": "cancelar cita"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"}, # Añadido
            {"text": "Reiniciar", "action": "reiniciar"} # Añadido
        ]}

    elif next_step == "awaiting_service_for_booking":
        service = get_service_details(user_message_lower)
        if service:
            context['selected_service_code'] = service["code"]
            context['booking_details'] = {"service_code": service["code"]}
            response_text = f"Has elegido **{service['name']}**. ¿Para qué fecha te gustaría agendar? (Formato AAAA-MM-DD, ej. 2025-07-30)"
            next_step = "awaiting_booking_date"
        else:
            response_text = "Ese servicio no está en mi lista. Por favor, intenta con otro nombre o escribe 'servicios' para ver la lista completa."

    elif next_step == "awaiting_booking_date" or next_step == "awaiting_reschedule_date":
        date_obj = validate_date(user_message)
        if user_message_lower == "hoy":
            date_obj = datetime.date.today()
        elif user_message_lower == "mañana" or user_message_lower == "manana":
            date_obj = datetime.date.today() + datetime.timedelta(days=1)
        elif user_message_lower == "pasado mañana" or user_message_lower == "pasado manana":
            date_obj = datetime.date.today() + datetime.timedelta(days=2)

        if date_obj:
            context['booking_details']['date'] = date_obj.isoformat()
            
            service_code_for_slots = context['selected_service_code']
            if next_step == "awaiting_reschedule_date" and 'current_booking_id_for_action' in context and context['current_booking_id_for_action'] in bookings_db:
                service_code_for_slots = bookings_db[context['current_booking_id_for_action']]['service_code']

            slots = get_available_slots(service_code_for_slots, context['booking_details']['date'])
            if slots:
                response_text = f"Perfecto. Aquí tienes los horarios disponibles para el {date_obj.isoformat()} para **{services_db[service_code_for_slots]['name']}**:"
                return_data = {
                    "type": "available_slots",
                    "date": date_obj.isoformat(),
                    "slots": slots,
                    "service_code": service_code_for_slots
                }
                if next_step == "awaiting_reschedule_date":
                    next_step = "awaiting_reschedule_time"
                else:
                    next_step = "awaiting_booking_time"
            else:
                response_text = f"Lo siento, no hay slots disponibles para el {date_obj.isoformat()} o para este servicio. Por favor, elige otra fecha."
                # Añadir botones de sugerencia para elegir otra fecha
                return_data = {"type": "action_buttons", "buttons": [
                    {"text": "Hoy", "action": "hoy"},
                    {"text": "Mañana", "action": "mañana"},
                    {"text": "Pasado mañana", "action": "pasado mañana"},
                    {"text": "Cancelar", "action": "cancelar"}
                ]}
        else:
            response_text = "Esa fecha no es válida. Por favor, usa el formato AAAA-MM-DD o di 'hoy', 'mañana', 'pasado mañana'."
            return_data = {"type": "action_buttons", "buttons": [
                {"text": "Hoy", "action": "hoy"},
                {"text": "Mañana", "action": "mañana"},
                {"text": "Pasado mañana", "action": "pasado mañana"},
                {"text": "Cancelar", "action": "cancelar"}
            ]}

    elif next_step == "awaiting_booking_time" or next_step == "awaiting_reschedule_time":
        selected_time = user_message_lower.replace('-', ':')
        
        if user_message_lower.startswith("slot_selected_"):
            parts = user_message_lower.split('_')
            if len(parts) >= 4:
                selected_date_from_button = parts[2]
                selected_time = parts[3].replace('-', ':')
            else:
                response_text = "Lo siento, hubo un problema al procesar la selección del slot. Por favor, inténtalo de nuevo."
                next_step = context.get('last_step', 'main_menu')
                context['step'] = next_step
                return_data = {"type": "action_buttons", "buttons": [
                    {"text": "Ver servicios", "action": "servicios"},
                    {"text": "Agendar una cita", "action": "agendar cita"}
                ]}
                return {"response": response_text, "context": context, "data": return_data}

            if selected_date_from_button != context['booking_details'].get('date'):
                response_text = "La hora seleccionada no corresponde a la fecha esperada. Por favor, vuelve a elegir."
                # Devuelve los slots disponibles nuevamente
                service_code_for_slots = context['selected_service_code'] if 'selected_service_code' in context else (bookings_db[context['current_booking_id_for_action']]['service_code'] if 'current_booking_id_for_action' in context and context['current_booking_id_for_action'] in bookings_db else None)
                slots = get_available_slots(service_code_for_slots, context['booking_details']['date'])
                return_data = {
                    "type": "available_slots",
                    "date": context['booking_details']['date'],
                    "slots": slots,
                    "service_code": service_code_for_slots
                }
            elif not validate_time(selected_time):
                response_text = "La hora seleccionada no es válida. Por favor, elige de los slots disponibles."
                service_code_for_slots = context['selected_service_code'] if 'selected_service_code' in context else (bookings_db[context['current_booking_id_for_action']]['service_code'] if 'current_booking_id_for_action' in context and context['current_booking_id_for_action'] in bookings_db else None)
                slots = get_available_slots(service_code_for_slots, context['booking_details']['date'])
                return_data = {
                    "type": "available_slots",
                    "date": context['booking_details']['date'],
                    "slots": slots,
                    "service_code": service_code_for_slots
                }
            else:
                context['booking_details']['time'] = selected_time
                if next_step == "awaiting_reschedule_time":
                    booking_id = context['current_booking_id_for_action']
                    old_booking = bookings_db.get(booking_id)
                    if old_booking:
                        old_booking['date'] = context['booking_details']['date']
                        old_booking['time'] = context['booking_details']['time']
                        bookings_db[booking_id] = old_booking
                        
                        response_text = f"¡Listo! Tu reserva **{booking_id}** ha sido reagendada para el **{old_booking['date']} a las {old_booking['time']}**."
                        next_step = "booking_confirmed"
                        context['current_booking_id_for_action'] = None
                        context['booking_details'] = {}
                        return_data = {"type": "action_buttons", "buttons": [
                            {"text": "Ver servicios", "action": "servicios"},
                            {"text": "Agendar una cita", "action": "agendar cita"},
                            {"text": "Reagendar cita", "action": "reagendar cita"},
                            {"text": "Cancelar cita", "action": "cancelar cita"}
                        ]}
                    else:
                        response_text = "Lo siento, la reserva original no fue encontrada para reagendar."
                        next_step = "main_menu"
                        return_data = {"type": "action_buttons", "buttons": [
                            {"text": "Ver servicios", "action": "servicios"},
                            {"text": "Agendar una cita", "action": "agendar cita"},
                            {"text": "Reagendar cita", "action": "reagendar cita"},
                            {"text": "Cancelar cita", "action": "cancelar cita"}
                        ]}
                else:
                    response_text = "¡Excelente! ¿Cuál es tu nombre completo para esta reserva?"
                    next_step = "awaiting_client_name_for_booking"
        else: # El usuario ingresó la hora manualmente
            chosen_time_manual = validate_time(user_message_lower)
            if chosen_time_manual:
                date_for_slots = context['booking_details'].get('date')
                service_code_for_slots = context['selected_service_code'] if 'selected_service_code' in context else (bookings_db[context['current_booking_id_for_action']]['service_code'] if 'current_booking_id_for_action' in context and context['current_booking_id_for_action'] in bookings_db else None)

                if not service_code_for_slots:
                    response_text = "Lo siento, no pude determinar el servicio para esta cita. Por favor, comienza de nuevo."
                    next_step = "main_menu"
                    return_data = {"type": "action_buttons", "buttons": [
                        {"text": "Ver servicios", "action": "servicios"},
                        {"text": "Agendar una cita", "action": "agendar cita"},
                        {"text": "Reagendar cita", "action": "reagendar cita"},
                        {"text": "Cancelar cita", "action": "cancelar cita"}
                    ]}
                    context['step'] = next_step
                    return {"response": response_text, "context": context, "data": return_data}

                available_slots_for_date = get_available_slots(service_code_for_slots, date_for_slots)

                if chosen_time_manual in available_slots_for_date:
                    context['booking_details']['time'] = chosen_time_manual
                    if next_step == "awaiting_reschedule_time":
                        booking_id = context['current_booking_id_for_action']
                        old_booking = bookings_db.get(booking_id)
                        if old_booking:
                            old_booking['date'] = context['booking_details']['date']
                            old_booking['time'] = context['booking_details']['time']
                            bookings_db[booking_id] = old_booking
                            
                            response_text = f"¡Listo! Tu reserva **{booking_id}** ha sido reagendada para el **{old_booking['date']} a las {old_booking['time']}**."
                            next_step = "booking_confirmed"
                            context['current_booking_id_for_action'] = None
                            context['booking_details'] = {}
                            return_data = {"type": "action_buttons", "buttons": [
                                {"text": "Ver servicios", "action": "servicios"},
                                {"text": "Agendar una cita", "action": "agendar cita"},
                                {"text": "Reagendar cita", "action": "reagendar cita"},
                                {"text": "Cancelar cita", "action": "cancelar cita"}
                            ]}
                        else:
                            response_text = "Lo siento, la reserva original no fue encontrada para reagendar."
                            next_step = "main_menu"
                            return_data = {"type": "action_buttons", "buttons": [
                                {"text": "Ver servicios", "action": "servicios"},
                                {"text": "Agendar una cita", "action": "agendar cita"},
                                {"text": "Reagendar cita", "action": "reagendar cita"},
                                {"text": "Cancelar cita", "action": "cancelar cita"}
                            ]}
                    else:
                        response_text = "¡Excelente! ¿Cuál es tu nombre completo para esta reserva?"
                        next_step = "awaiting_client_name_for_booking"
                else:
                    response_text = f"La hora {chosen_time_manual} no está disponible para el servicio y fecha seleccionados. Por favor, elige una de las horas mostradas o prueba con 'Elegir otra fecha'."
                    # Devolver los slots nuevamente
                    slots = get_available_slots(service_code_for_slots, date_for_slots)
                    return_data = {
                        "type": "available_slots",
                        "date": date_for_slots,
                        "slots": slots,
                        "service_code": service_code_for_slots
                    }
            else:
                response_text = "Formato de hora no válido. Por favor, usa HH:MM (ej. 14:30)."
                # Devolver los slots nuevamente si es un error de formato
                service_code_for_slots = context['selected_service_code'] if 'selected_service_code' in context else (bookings_db[context['current_booking_id_for_action']]['service_code'] if 'current_booking_id_for_action' in context and context['current_booking_id_for_action'] in bookings_db else None)
                if service_code_for_slots and context['booking_details'].get('date'):
                    slots = get_available_slots(service_code_for_slots, context['booking_details']['date'])
                    return_data = {
                        "type": "available_slots",
                        "date": context['booking_details']['date'],
                        "slots": slots,
                        "service_code": service_code_for_slots
                    }
                else: # Si no tenemos suficiente contexto para mostrar slots, volvemos a las opciones principales
                    return_data = {"type": "action_buttons", "buttons": [
                        {"text": "Ver servicios", "action": "servicios"},
                        {"text": "Agendar una cita", "action": "agendar cita"},
                        {"text": "Reagendar cita", "action": "reagendar cita"},
                        {"text": "Cancelar cita", "action": "cancelar cita"}
                    ]}


    elif next_step == "awaiting_client_name_for_booking":
        if len(user_message.strip()) > 2:
            context['booking_details']['client_name'] = user_message.strip()
            response_text = "¿Y cuál es tu número de teléfono (con código de país, ej. +5491112345678) para contactarte si es necesario?"
            next_step = "awaiting_client_phone_for_booking"
        else:
            response_text = "Por favor, ingresa un nombre completo válido."

    elif next_step == "awaiting_client_phone_for_booking":
        phone = validate_phone(user_message) 
        if phone:
            context['booking_details']['client_phone'] = phone
            service = services_db.get(context['selected_service_code'])
            if service:
                booking_id = generate_booking_id()
                bookings_db[booking_id] = context['booking_details']
                
                response_text = f"¡Listo! Tu cita para **{service['name']}** ha sido agendada para el **{context['booking_details']['date']} a las {context['booking_details']['time']}** a nombre de **{context['booking_details']['client_name']}**. Tu número de reserva es **{booking_id}**. Te enviaremos una confirmación a tu teléfono **{phone}**."
                
                next_step = "booking_confirmed"
                context['selected_service_code'] = None
                context['booking_details'] = {}
                context['action_type'] = None
                context['current_booking_id_for_action'] = None
                context['contact_info'] = {}
                return_data = {"type": "action_buttons", "buttons": [ # Añadir botones al finalizar con éxito
                    {"text": "Ver servicios", "action": "servicios"},
                    {"text": "Agendar una cita", "action": "agendar cita"},
                    {"text": "Reagendar cita", "action": "reagendar cita"},
                    {"text": "Cancelar cita", "action": "cancelar cita"}
                ]}
            else:
                response_text = "Lo siento, no pude confirmar el servicio para tu reserva. Por favor, intenta agendar de nuevo."
                next_step = "main_menu"
                return_data = {"type": "action_buttons", "buttons": [
                    {"text": "Ver servicios", "action": "servicios"},
                    {"text": "Agendar una cita", "action": "agendar cita"},
                    {"text": "Reagendar cita", "action": "reagendar cita"},
                    {"text": "Cancelar cita", "action": "cancelar cita"}
                ]}
        else:
            response_text = "Ese número de teléfono no parece válido. Por favor, ingresa tu número con código de país (ej. +5491112345678)."

    elif next_step == "awaiting_booking_id_for_action":
        booking_id_input = user_message.strip().upper()
        if not re.match(r'^AGB-\d+$', booking_id_input): # Validar con el nuevo formato AGB-XXXX
            response_text = "El formato del ID de reserva no es válido. Debe ser como 'AGB-XXXX'."
        elif booking_id_input in bookings_db:
            context['current_booking_id_for_action'] = booking_id_input
            action_type = context.get('action_type')
            booking = bookings_db[booking_id_input]
            service_name = services_db[booking['service_code']]['name']

            if action_type == 'reschedule':
                response_text = f"Entendido. Tu reserva actual para **{service_name}** el **{booking['date']} a las {booking['time']}** ha sido encontrada. ¿Para qué nueva fecha te gustaría reagendar? (Formato AAAA-MM-DD o 'hoy', 'mañana')"
                next_step = "awaiting_reschedule_date"
            elif action_type == 'cancel':
                response_text = f"Confirma que deseas cancelar tu reserva para **{service_name}** el **{booking['date']} a las {booking['time']}** a nombre de **{booking['client_name']}**. Escribe 'confirmar cancelar' para proceder."
                next_step = "confirm_cancel_booking"
                # AÑADIDO: Envía el botón "confirmar cancelar"
                return_data = {"type": "action_buttons", "buttons": [
                    {"text": "confirmar cancelar", "action": "confirmar cancelar"},
                    {"text": "No, volver al menú", "action": "reiniciar"}
                ]}
            else:
                response_text = "No entendí la acción. Por favor, di 'cancelar' o 'reagendar' después de dar el ID."
        else:
            response_text = "Lo siento, no encontré ninguna reserva con ese ID. Por favor, verifica y vuelve a intentarlo, o escribe 'hablar con un asesor' si necesitas ayuda."

    elif next_step == "confirm_cancel_booking":
        if user_message_lower == "confirmar cancelar":
            if context.get('current_booking_id_for_action') in bookings_db:
                del bookings_db[context['current_booking_id_for_action']]
                response_text = f"Tu reserva con ID **{context['current_booking_id_for_action']}** ha sido cancelada con éxito. Esperamos verte pronto."
                next_step = "main_menu"
                context['current_booking_id_for_action'] = None
                context['action_type'] = None
                context['booking_details'] = {}
                context['selected_service_code'] = None
                return_data = {"type": "action_buttons", "buttons": [
                    {"text": "Ver servicios", "action": "servicios"},
                    {"text": "Agendar una cita", "action": "agendar cita"},
                    {"text": "Reagendar cita", "action": "reagendar cita"},
                    {"text": "Cancelar cita", "action": "cancelar cita"}
                ]}
            else:
                response_text = "No se pudo encontrar la reserva para cancelar. Por favor, verifica el ID."
                next_step = "awaiting_booking_id_for_action"
        else:
            response_text = "Cancelación no confirmada. ¿Necesitas algo más o deseas volver al menú principal?"
            next_step = "main_menu"
            context['current_booking_id_for_action'] = None
            context['action_type'] = None
            context['booking_details'] = {}
            context['selected_service_code'] = None
            return_data = {"type": "action_buttons", "buttons": [
                {"text": "Ver servicios", "action": "servicios"},
                {"text": "Agendar una cita", "action": "agendar cita"},
                {"text": "Reagendar cita", "action": "reagendar cita"},
                {"text": "Cancelar cita", "action": "cancelar cita"}
            ]}
    
    elif next_step == "collect_contact_for_human_agendabot":
        if 'contact_info' not in context or not isinstance(context['contact_info'], dict):
            context['contact_info'] = {}

        name_match = re.search(r'(?:soy|mi nombre es|me llamo)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)', user_message_lower)
        phone_raw_match = re.search(r'(\+?\d[\d\s\-\(\)]{6,})', user_message)
        
        client_name = name_match.group(1).strip().title() if name_match else None
        client_phone = validate_phone(phone_raw_match.group(1)) if phone_raw_match else None

        if client_name and client_phone:
            context['contact_info']['name'] = client_name
            context['contact_info']['phone'] = client_phone
            response_text = f"Gracias, **{client_name}**. Un asesor se pondrá en contacto contigo en el **{client_phone}** en breve para ayudarte personalmente. ¿Hay algo más en lo que pueda asistirte mientras tanto?"
            next_step = "human_contact_collected"
            context['action_type'] = None
            context['contact_info'] = {}
            return_data = {"type": "action_buttons", "buttons": [ # Añadir botones al finalizar con éxito
                {"text": "Ver servicios", "action": "servicios"},
                {"text": "Agendar una cita", "action": "agendar cita"},
                {"text": "Reagendar cita", "action": "reagendar cita"},
                {"text": "Cancelar cita", "action": "cancelar cita"},
                {"text": "Hablar con un asesor", "action": "hablar con un asesor"}, # Añadido
                {"text": "Reiniciar", "action": "reiniciar"} # Añadido
            ]}
        else:
            missing_info = []
            if not client_name: missing_info.append("nombre")
            if not client_phone: missing_info.append("número de teléfono")
            response_text = f"No pude extraer tu {' y '.join(missing_info)}. Por favor, asegúrate de incluirlos claramente, como en el ejemplo: 'Soy Laura Gómez, mi teléfono es +5491112345678'."
            next_step = "collect_contact_for_human_agendabot"

    else:
        response_text = (
            "Disculpa, no logré entender tu consulta. Soy AgendaBot, tu asistente de agendamiento. "
            "Mis funciones principales son:\n"
            "• **Ver servicios**\n"
            "• **Agendar citas**\n"
            "• **Reagendar/Cancelar**\n"
            "• **Hablar con un asesor**\n\n"
            "¿En qué te puedo asistir específicamente?"
        )
        next_step = "main_menu"
        return_data = {"type": "action_buttons", "buttons": [
            {"text": "Ver servicios", "action": "servicios"},
            {"text": "Agendar una cita", "action": "agendar cita"},
            {"text": "Reagendar cita", "action": "reagendar cita"},
            {"text": "Cancelar cita", "action": "cancelar cita"},
            {"text": "Hablar con un asesor", "action": "hablar con un asesor"}, # Añadido
            {"text": "Reiniciar", "action": "reiniciar"} # Añadido
        ]}

    context['step'] = next_step
    return {
        "response": response_text,
        "context": context,
        "data": return_data
    }

# --- Rutas de la API de Flask ---

@app.route('/api/agendabot_chat', methods=['POST'])
def agendabot_chat_webhook():
    try:
        user_input = request.json.get('message', '')
        user_id = request.json.get('user_id', 'web_user_default')

        context = conversation_contexts.get(user_id, {
            "step": "welcome",
            "selected_service_code": None,
            "booking_details": {},
            "contact_info": {}
        })
        
        print(f"DEBUG_WEBHOOK: Mensaje recibido: '{user_input}', Contexto inicial: {context}")

        result = handle_agendabot_message(user_input, context)
        
        conversation_contexts[user_id] = result["context"]
        
        print(f"DEBUG_WEBHOOK: Respondiendo: '{result['response']}', Contexto actualizado: {result['context']}, Datos: {result['data']}")

        return jsonify(result)

    except Exception as e:
        print(f"ERROR_WEBHOOK: Error en agendabot_chat_webhook: {e}", file=sys.stderr)
        return jsonify({
            "response": "Lo siento, hubo un error técnico inesperado en el servidor. Por favor, intenta de nuevo.",
            "context": {"step": "main_menu", "selected_service_code": None, "booking_details": {}, "contact_info": {}},
            "data": {"type": "action_buttons", "buttons": [ # Asegurar botones en caso de error
                {"text": "Ver servicios", "action": "servicios"},
                {"text": "Agendar una cita", "action": "agendar cita"},
                {"text": "Reagendar cita", "action": "reagendar cita"},
                {"text": "Cancelar cita", "action": "cancelar cita"}
            ]}
        }), 500


# --- Endpoint de prueba (opcional) ---
@app.route('/')
def home():
    return "AgendaBot (core) is running! Use /api/agendabot_chat for web interactions. Other channels use their specific connectors."

# --- Ejecución del servidor Flask ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port, debug=True)

