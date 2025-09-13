import os
import logging
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import google.generativeai as genai

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

from pydantic import ConfigDict

class RebecaAgent:
    model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
    
    def __init__(self):
        print("Iniciando RebecaAgent...")
        
        # Verificar variables de entorno
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        print(f"SLACK_BOT_TOKEN presente: {bool(self.slack_token)}")
        print(f"GEMINI_API_KEY presente: {bool(self.gemini_key)}")
        
        # Inicializar el cliente de Slack
        self.slack_client = WebClient(token=self.slack_token)
        print("Cliente de Slack inicializado")
        print("Inicialización de RebecaAgent completada")

    def process_with_gemini(self, message: dict) -> dict:
        try:
            logger.info("Configurando Gemini...")
            if not self.gemini_key:
                raise ValueError("GEMINI_API_KEY no está configurada")
                
            # Inicializar el cliente de Gemini
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("Gemini configurado correctamente")
            
            # Validar el contenido del mensaje
            if not message.get('content'):
                raise ValueError("El mensaje está vacío")
            
            logger.info(f"Generando respuesta para: {message['content'][:100]}...")
            
            # Generar respuesta con manejo de errores específicos
            try:
                response = model.generate_content(message['content'])
                
                if not response.text:
                    raise ValueError("Gemini generó una respuesta vacía")
                    
                logger.info("Respuesta generada exitosamente")
                logger.debug(f"Respuesta completa: {response.text[:100]}...")
                
                return {'content': response.text}
                
            except Exception as e:
                if 'BlockedPrompt' in str(type(e)):
                    logger.error(f"Prompt bloqueado por políticas de seguridad: {str(e)}")
                    return {'content': 'Lo siento, no puedo procesar ese tipo de contenido.'}
                elif 'NotFound' in str(type(e)):
                    logger.error(f"Error de configuración del modelo Gemini: {str(e)}")
                    return {'content': 'Lo siento, hay un problema con la configuración del modelo. Por favor, contacta al administrador.'}
                else:
                    logger.error(f"Error durante la generación: {str(e)}")
                    return {'content': 'Hubo un problema al generar la respuesta. Por favor, intenta reformular tu mensaje.'}
                
        except Exception as e:
            logger.error(f"Error en process_with_gemini: {str(e)}")
            logger.exception("Detalles del error:")
            raise

    def process_message(self, message) -> dict:
        try:
            # Convertir el mensaje a diccionario si es un objeto Message
            message_dict = {
                'content': message.content,
                'author': message.author,
                'slack_channel': message.slack_channel
            } if hasattr(message, 'content') else message
            
            # Validar el mensaje
            if not message_dict or not all(key in message_dict for key in ['content', 'author', 'slack_channel']):
                logger.error("Mensaje inválido o campos faltantes")
                return {'content': 'El mensaje está incompleto o tiene un formato inválido.'}
            
            # Agregar reacción de ojos al mensaje
            try:
                self.slack_client.reactions_add(
                    channel=message_dict['slack_channel'],
                    name='eyes',
                    timestamp=message.ts
                )
            except SlackApiError as e:
                logger.error(f"Error al agregar reacción: {str(e)}")
            
            # Procesar el mensaje usando Gemini
            logger.info("Iniciando procesamiento del mensaje...")
            response = self.process_with_gemini(message_dict)
            
            # Validar la respuesta
            if not isinstance(response, dict) or 'content' not in response:
                logger.warning(f"Respuesta con formato inválido: {response}")
                response = {'content': str(response)}
            
            if not response['content'].strip():
                logger.error("Respuesta vacía recibida")
                return {'content': 'Lo siento, no pude generar una respuesta válida.'}
            
            # Remover reacción de ojos y agregar paloma verde
            try:
                self.slack_client.reactions_remove(
                    channel=message_dict['slack_channel'],
                    name='eyes',
                    timestamp=message.ts
                )
                self.slack_client.reactions_add(
                    channel=message_dict['slack_channel'],
                    name='white_check_mark',
                    timestamp=message.ts
                )
            except SlackApiError as e:
                logger.error(f"Error al actualizar reacciones: {str(e)}")
            
            logger.info("Mensaje procesado exitosamente")
            return response
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {str(e)}")
            logger.exception("Detalles del error:")
            return {'content': 'Lo siento, ocurrió un error al procesar tu mensaje. Por favor, intenta de nuevo.'}

def create_agent():
    return RebecaAgent()

if __name__ == "__main__":
    agent = create_agent()
    # Aquí podríamos agregar la lógica para ejecutar el agente