import os
from dotenv import load_dotenv
from slack_handler import start_slack_handler

def verificar_variables_entorno():
    variables_requeridas = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'GEMINI_API_KEY']
    variables_faltantes = []
    
    for var in variables_requeridas:
        valor = os.getenv(var)
        if not valor:
            variables_faltantes.append(var)
        print(f"Variable {var}: {'PRESENTE' if valor else 'FALTANTE'}")
        if valor:
            print(f"Longitud de {var}: {len(valor)} caracteres")
    
    return len(variables_faltantes) == 0

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
        start_slack_handler()
        print("Rebeca está lista y escuchando mensajes de Slack!")
        
        # Mantener el proceso principal en ejecución
        import time
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"\n¡ERROR! Error al iniciar Rebeca: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
    except KeyboardInterrupt:
        print("\nDeteniendo Rebeca...")
    finally:
        print("="*50)

if __name__ == "__main__":
    main()