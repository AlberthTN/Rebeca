import os
from dotenv import load_dotenv
from slack_handler import start_slack_handler
from rebeca_agent import create_agent
from threading import Thread
import time

def verificar_variables_entorno():
    variables_requeridas = [
        'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'GEMINI_API_KEY',
        'BIGQUERY_PROJECT_ID', 'BIGQUERY_DATASET', 'GOOGLE_APPLICATION_CREDENTIALS_JSON'
    ]
    variables_faltantes = []
    
    for var in variables_requeridas:
        valor = os.getenv(var)
        if not valor:
            variables_faltantes.append(var)
        print(f"Variable {var}: {'PRESENTE' if valor else 'FALTANTE'}")
        if valor and var != 'GOOGLE_APPLICATION_CREDENTIALS_JSON':
            print(f"Longitud de {var}: {len(valor)} caracteres")
    
    return len(variables_faltantes) == 0

def check_reminders_loop(agent):
    """Función que se ejecuta en un hilo separado para verificar recordatorios."""
    while True:
        try:
            agent.check_reminders()
        except Exception as e:
            print(f"Error al verificar recordatorios: {str(e)}")
        time.sleep(60)  # Verificar cada minuto

def main():
    print("="*50)
    print("Iniciando Rebeca - Agente Multi-herramientas")
    print("="*50)
    
    # Cargar variables de entorno
    load_dotenv()
    print("\nVerificando variables de entorno...")
    if not verificar_variables_entorno():
        print("\n¡ERROR! Faltan variables de entorno requeridas")
        return
    
    print("\nConectando con Slack...")
    try:
        # Crear la instancia del agente
        agent = create_agent()
        
        # Iniciar el hilo de monitoreo de recordatorios
        reminder_thread = Thread(target=check_reminders_loop, args=(agent,), daemon=True)
        reminder_thread.start()
        print("Monitoreo de recordatorios iniciado!")
        
        # Iniciar el manejador de Slack con la instancia del agente
        print("Rebeca está lista y escuchando mensajes de Slack!")
        start_slack_handler(agent)
    except Exception as e:
        print(f"\n¡ERROR! Error al iniciar Rebeca: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
    except KeyboardInterrupt:
        print("\nDeteniendo Rebeca...")
    finally:
        print("="*50)

if __name__ == "__main__":
    main()