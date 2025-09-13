import os
import json
import datetime
import logging
import google.generativeai as genai
from datetime import datetime
from slack_handler import SlackHandler
from reminder_handler import ReminderHandler

class RebecaAgent:
    def __init__(self):
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Inicializar el cliente de Slack y el ReminderHandler
        self.slack_handler = SlackHandler()
        self.reminder_handler = ReminderHandler(
            project_id=os.getenv('BIGQUERY_PROJECT_ID'),
            dataset_id=os.getenv('BIGQUERY_DATASET')
        )
        
        # Configurar Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        # Usar la versión más reciente y estable del modelo
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        # Configurar la generación
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            candidate_count=1,
            stop_sequences=None,
            max_output_tokens=2048,
            top_p=0.8,
            top_k=40
        )
        
    def _analyze_intent(self, message):
        try:
            current_time = datetime.now()
            prompt = f"""Analiza el siguiente mensaje y determina si es una solicitud para establecer un recordatorio.
            Si es un recordatorio, extrae la fecha/hora y la descripción. Presta especial atención a expresiones de tiempo relativas como 'en 5 minutos', 'mañana a las 3', etc.
            
            Hora actual: {current_time.strftime('%Y-%m-%d %H:%M')}
            Mensaje: {message}
            
            Si el mensaje contiene una solicitud de recordatorio, convierte la fecha/hora a formato absoluto (YYYY-MM-DD HH:MM) basado en la hora actual proporcionada.
            Por ejemplo:
            - 'en 5 minutos' → calcular 5 minutos desde la hora actual
            - 'mañana a las 3pm' → usar la fecha de mañana con la hora especificada
            
            Responde en formato JSON con esta estructura:
            {{
                "is_reminder": true/false,
                "datetime": "YYYY-MM-DD HH:MM" (si aplica, en formato absoluto),
                "description": "descripción del recordatorio" (si aplica)
            }}
            
            La fecha y hora DEBEN estar en formato absoluto, no uses expresiones relativas en la respuesta.
            """
            
            # Configurar el modelo para generar solo JSON
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config,
                    safety_settings=safety_settings
                )
                
                if not response or not response.parts:
                    self.logger.error("Respuesta vacía del modelo")
                    return {"is_reminder": False}
                
                response_text = response.parts[0].text.strip()
                self.logger.info(f"Respuesta del modelo: {response_text}")
                
                # Buscar estructura JSON en la respuesta
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    self.logger.error("No se encontró estructura JSON en la respuesta")
                    return {"is_reminder": False}
                
                json_str = response_text[start_idx:end_idx + 1]
                self.logger.info(f"JSON extraído: {json_str}")
                
                try:
                    result = json.loads(json_str)
                    self.logger.info(f"JSON parseado exitosamente: {result}")
                    
                    if not isinstance(result, dict):
                        self.logger.error("La respuesta no es un objeto JSON válido")
                        return {"is_reminder": False}
                    
                    if 'is_reminder' not in result:
                        self.logger.warning("Campo 'is_reminder' no encontrado, estableciendo como False")
                        return {"is_reminder": False}
                    
                    if result.get('is_reminder', False):
                        if not all(key in result for key in ['datetime', 'description']):
                            self.logger.error("Faltan campos requeridos en el recordatorio")
                            return {"is_reminder": False}
                        
                        try:
                            parsed_datetime = datetime.strptime(result['datetime'], "%Y-%m-%d %H:%M")
                            if parsed_datetime < datetime.now():
                                self.logger.error("La fecha del recordatorio es en el pasado")
                                return {"is_reminder": False}
                        except ValueError as e:
                            self.logger.error(f"Error al parsear datetime: {str(e)}")
                            return {"is_reminder": False}
                    
                    return result
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error al decodificar JSON: {str(e)}")
                    return {"is_reminder": False}
                    
            except Exception as e:
                self.logger.error(f"Error al generar contenido: {str(e)}")
                return {"is_reminder": False}
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Error al decodificar JSON: {str(e)}")
                self.logger.error(f"Texto que causó el error: {response.parts[0].text}")
                
                # Intento de recuperación: buscar estructura JSON en la respuesta
                response_text = response.parts[0].text.strip()
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    try:
                        json_str = response_text[start_idx:end_idx + 1]
                        self.logger.info(f"Intentando parsear JSON extraído: {json_str}")
                        result = json.loads(json_str)
                        return result
                    except json.JSONDecodeError:
                        pass
                
                # Si todos los intentos fallan, devolver un resultado por defecto
                self.logger.warning("Fallando a respuesta por defecto")
                return {"is_reminder": False}
            
        except Exception as e:
            self.logger.error(f"Error al analizar el intent: {str(e)}")
            return {"is_reminder": False}
    
    def _parse_time(self, time_str):
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except Exception as e:
            self.logger.error(f"Error al parsear el tiempo: {str(e)}")
            return None

    def process_message(self, message, channel_id, user_id):
        try:
            self.logger.info("Iniciando procesamiento del mensaje...")
            
            # Analizar el intent del mensaje
            intent = self._analyze_intent(message)
            
            if intent.get("is_reminder", False):
                # Procesar recordatorio
                reminder_time = self._parse_time(intent["datetime"])
                if reminder_time:
                    self.reminder_handler.create_reminder(
                        user_id=user_id,
                        message=intent["description"],
                        channel_id=channel_id,
                        reminder_datetime=reminder_time
                    )
                    # Generar confirmación personalizada del recordatorio
                    confirm_prompt = f"Genera un mensaje amigable para confirmar que he programado un recordatorio. Detalles:\nFecha y hora: {intent['datetime']}\nDescripción: {intent['description']}\n\nReglas:\n- Usa emojis de Slack apropiados\n- Confirma claramente la fecha/hora y el mensaje\n- Añade una frase amigable\n- Usa formato compatible con Slack markdown\n- No uses más de 3 emojis\n- Mantén el mensaje conciso"

                    try:
                        response = self.model.generate_content(confirm_prompt, generation_config=self.generation_config)
                        if response and response.parts:
                            return response.parts[0].text.strip()
                        else:
                            return f":calendar: He programado un recordatorio para {intent['datetime']}: {intent['description']}"
                    except Exception as e:
                        self.logger.error(f"Error al generar confirmación personalizada: {str(e)}")
                        return f":calendar: He programado un recordatorio para {intent['datetime']}: {intent['description']}"
                else:
                    return "Lo siento, no pude entender la fecha y hora del recordatorio."
            else:
                # Procesar mensaje general con Gemini
                return self.process_with_gemini(message)
                
        except Exception as e:
            self.logger.error(f"Error al procesar el mensaje: {str(e)}")
            return "Lo siento, hubo un error al procesar tu mensaje."

    def process_with_gemini(self, message):
        try:
            self.logger.info("Iniciando procesamiento con Gemini...")
            self.logger.info(f"Mensaje a procesar: {message}")
            
            # Verificar la API key antes de hacer la llamada
            if not os.getenv('GEMINI_API_KEY'):
                self.logger.error("GEMINI_API_KEY no está configurada")
                return "Lo siento, hay un problema con la configuración de la API. Por favor, contacta al administrador."

            try:
                # Modificar el prompt para generar respuestas compatibles con Slack
                prompt = f"Actúa como un asistente amigable y profesional. Responde al siguiente mensaje: {message}\n\nReglas para la respuesta:\n- Usa formato compatible con Slack markdown cuando sea apropiado\n- Incluye emojis relevantes al contexto (máximo 3)\n- Mantén un tono amigable y profesional\n- Si la respuesta incluye código, usa bloques de código con ```\n- Si la respuesta incluye listas, usa formato de lista de Slack\n- Mantén las respuestas concisas y bien estructuradas"

                response = self.model.generate_content(prompt, generation_config=self.generation_config)
                self.logger.info("Respuesta recibida de Gemini")
            except Exception as e:
                self.logger.error(f"Error al llamar a la API de Gemini: {str(e)}")
                return ":warning: Lo siento, hubo un problema al comunicarse con el modelo. Por favor, intenta de nuevo más tarde."

            if not response:
                self.logger.error("Respuesta vacía de Gemini")
                return "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."
            
            if not hasattr(response, 'parts') or not response.parts:
                self.logger.error("Respuesta de Gemini no tiene el formato esperado")
                return "Lo siento, la respuesta no tiene el formato esperado. Por favor, intenta de nuevo."
            
            self.logger.info("Procesando respuesta de Gemini...")
            result = response.parts[0].text
            self.logger.info(f"Respuesta procesada exitosamente: {result[:100]}...")
            return result
            
        except Exception as e:
            self.logger.error(f"Error al procesar con Gemini: {str(e)}")
            self.logger.error(f"Tipo de error: {type(e).__name__}")
            return "Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo más tarde."

    def check_reminders(self):
        try:
            due_reminders = self.reminder_handler.get_pending_reminders()
            for reminder in due_reminders:
                try:
                    # Si el canal comienza con 'D', es un DM y debemos usar el user_id
                    channel_to_use = reminder.user_id if reminder.channel_id.startswith('D') else reminder.channel_id
                    
                    # Generar un mensaje personalizado para el recordatorio usando Gemini
                    prompt = f"Genera un mensaje amigable y profesional para notificar un recordatorio en Slack. El mensaje es: {reminder.message}. \nReglas:\n- Usa emojis de Slack apropiados al contexto\n- Incluye el mensaje original entre comillas o en un blockquote\n- Añade una frase motivadora o amigable al final\n- El formato debe ser compatible con el markdown de Slack\n- Varía el estilo y no uses siempre la misma estructura\n- No uses más de 4 emojis en total\n- Mantén el mensaje conciso"

                    try:
                        response = self.model.generate_content(prompt, generation_config=self.generation_config)
                        if response and response.parts:
                            formatted_message = response.parts[0].text.strip()
                        else:
                            formatted_message = f":bell: Recordatorio: {reminder.message}"
                    except Exception as e:
                        self.logger.error(f"Error al generar mensaje personalizado: {str(e)}")
                        formatted_message = f":bell: Recordatorio: {reminder.message}"
                    
                    self.slack_handler.send_message(
                        channel_id=channel_to_use,
                        message=formatted_message
                    )
                    self.reminder_handler.mark_reminder_as_executed(reminder.reminder_id)
                except Exception as e:
                    self.logger.error(f"Error al enviar recordatorio {reminder.reminder_id}: {str(e)}")
                    continue
        except Exception as e:
            self.logger.error(f"Error al verificar recordatorios: {str(e)}")

def create_agent():
    return RebecaAgent()