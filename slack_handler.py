import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from rebeca_agent import create_agent
import logging
from dataclasses import dataclass

@dataclass
class Message:
    content: str
    author: str
    slack_channel: str
    ts: str

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Verificar tokens de Slack
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_app_token = os.getenv("SLACK_APP_TOKEN")

if not slack_bot_token or not slack_app_token:
    raise ValueError("¡Error! Tokens de Slack no encontrados en variables de entorno")

logger.info("Tokens de Slack verificados correctamente")

# Inicializar la aplicación de Slack
app = App(token=slack_bot_token)
rebeca = create_agent()

@app.event("message")
def handle_message_events(event, say):
    # Verificar que tenemos todos los campos necesarios
    required_fields = ['type', 'channel', 'user', 'text']
    for field in required_fields:
        if field not in event:
            logger.error(f"Campo requerido '{field}' no encontrado en el evento")
            return
    logger.info("="*50)
    logger.info("PROCESAMIENTO DE MENSAJE ENTRANTE")
    logger.info("="*50)
    logger.debug(f"Evento completo recibido: {event}")
    logger.info(f"Tipo de evento: {event.get('type')}")
    logger.info(f"Canal: {event.get('channel')}")
    logger.info(f"Usuario: {event.get('user')}")
    logger.info(f"Texto: {event.get('text')}")
    
    # Ignorar mensajes del bot
    if 'bot_id' in event:
        logger.info("Ignorando mensaje de bot")
        return
        
    # Verificar si es un mensaje directo o mención
    is_dm = event.get('channel_type') == 'im'
    is_mention = 'app_mention' in event.get('type', '')
    
    if not (is_dm or is_mention):
        logger.info("Ignorando mensaje que no es DM ni mención")
        return
    
    logger.info("Procesando mensaje de usuario...")

    try:
        # Crear un mensaje para el agente
        message = Message(
            content=event['text'],
            author=event['user'],
            slack_channel=event['channel'],
            ts=event['ts']
        )
        logger.debug(f"Mensaje creado: {message.__dict__}")

        # Procesar el mensaje con Rebeca
        logger.info(f"Enviando mensaje al agente: {message.content}")
        response = rebeca.process_message(message)
        logger.debug(f"Respuesta del agente: {response}")
        
        # Validar y enviar respuesta
        if isinstance(response, dict) and 'content' in response:
            response_text = response['content']
        else:
            logger.warning(f"Respuesta inesperada del agente: {response}")
            response_text = str(response)

        # Verificar que la respuesta no está vacía
        if not response_text.strip():
            logger.error("Respuesta vacía del agente")
            say(text="Lo siento, no pude generar una respuesta válida.")
            return

        # Enviar respuesta a Slack
        logger.info(f"Enviando respuesta a Slack: {response_text[:100]}...")
        say(text=response_text)
        logger.info("Mensaje procesado y respondido exitosamente")
        
    except Exception as e:
        error_msg = f"Error al procesar mensaje: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.exception("Detalles del error:")
        say(text="Lo siento, ocurrió un error al procesar tu mensaje.")
    
    finally:
        logger.info("="*50)

def start_slack_handler():
    try:
        logger.info("Iniciando SocketModeHandler...")
        handler = SocketModeHandler(
            app=app,
            app_token=slack_app_token
        )
        
        # Configurar manejadores de eventos adicionales
        @app.event("app_mention")
        def handle_app_mentions(event, say):
            logger.info(f"Mención de app recibida: {event}")
            handle_message_events(event, say)

        @app.error
        def custom_error_handler(error, body, logger):
            logger.error(f"Error en la aplicación Slack: {error}")
            logger.debug(f"Contexto del error: {body}")

        # Iniciar el handler
        logger.info("Iniciando el servidor de Slack...")
        handler.start()
    except Exception as e:
        logger.error(f"Error al iniciar SocketModeHandler: {e}")
        raise

if __name__ == "__main__":
    start_slack_handler()