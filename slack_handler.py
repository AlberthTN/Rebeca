import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import logging
from dataclasses import dataclass

@dataclass
class Message:
    content: str
    author: str
    slack_channel: str
    ts: str

class SlackHandler:
    def __init__(self):
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Cargar variables de entorno
        load_dotenv()
        
        # Verificar tokens de Slack
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        if not self.slack_bot_token:
            raise ValueError("¡Error! SLACK_BOT_TOKEN no encontrado en variables de entorno")
            
        # Inicializar la aplicación de Slack
        self.app = App(token=self.slack_bot_token)
    
    def send_message(self, channel_id: str, message: str):
        try:
            # Verificar token antes de enviar
            if not self.slack_bot_token:
                self.logger.error("Token de Slack no encontrado")
                return

            # Verificar que el token comience con xoxb-
            if not self.slack_bot_token.startswith('xoxb-'):
                self.logger.error("Formato de token inválido")
                return

            # Verificar que el canal existe
            try:
                channel_info = self.app.client.conversations_info(channel=channel_id)
                if not channel_info['ok']:
                    self.logger.error(f"Error al verificar canal: {channel_info.get('error', 'Desconocido')}")
                    return
            except Exception as e:
                # Si es un DM, intentar abrir una conversación
                try:
                    conversation = self.app.client.conversations_open(users=channel_id)
                    if conversation['ok']:
                        channel_id = conversation['channel']['id']
                    else:
                        self.logger.error(f"Error al abrir conversación: {conversation.get('error', 'Desconocido')}")
                        return
                except Exception as e:
                    self.logger.error(f"Error al abrir conversación: {str(e)}")
                    return

            response = self.app.client.chat_postMessage(
                channel=channel_id,
                text=message
            )
            
            if not response['ok']:
                self.logger.error(f"Error al enviar mensaje: {response.get('error', 'Desconocido')}")
                return
                
        except Exception as e:
            self.logger.error(f"Error al enviar mensaje: {str(e)}")
            self.logger.error(f"Tipo de error: {type(e).__name__}")

def start_slack_handler(agent):
    try:
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
                # Agregar reacción de ojos al mensaje
                app.client.reactions_add(
                    channel=event['channel'],
                    timestamp=event['ts'],
                    name='eyes'
                )
                
                # Procesar el mensaje con el agente
                response = agent.process_message(
                    message=event['text'],
                    channel_id=event['channel'],
                    user_id=event['user']
                )
                
                # Enviar respuesta a Slack
                logger.info(f"Enviando respuesta a Slack: {response[:100]}...")
                say(text=response)
                
                # Quitar reacción de ojos y agregar flecha verde
                app.client.reactions_remove(
                    channel=event['channel'],
                    timestamp=event['ts'],
                    name='eyes'
                )
                app.client.reactions_add(
                    channel=event['channel'],
                    timestamp=event['ts'],
                    name='white_check_mark'
                )
                
                logger.info("Mensaje procesado y respondido exitosamente")
                
            except Exception as e:
                error_msg = f"Error al procesar mensaje: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Tipo de error: {type(e).__name__}")
                logger.exception("Detalles del error:")
                say(text="Lo siento, ocurrió un error al procesar tu mensaje.")
            
            finally:
                logger.info("="*50)
        
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
        try:
            handler.start()
            return agent
        except KeyboardInterrupt:
            logger.info("Deteniendo el servidor de Slack por interrupción del usuario...")
            if hasattr(handler, 'client') and handler.client:
                handler.client.close()
            return agent
        except Exception as e:
            logger.error(f"Error al iniciar el servidor de Slack: {str(e)}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            if hasattr(handler, 'client') and handler.client:
                handler.client.close()
            raise
        
    except Exception as e:
        logger.error(f"Error al iniciar SocketModeHandler: {e}")
        raise

if __name__ == "__main__":
    from rebeca_agent import create_agent
    start_slack_handler(create_agent())