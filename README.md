# Rebeca - Agente Multi-herramientas con Gemini y Slack

Rebeca es un agente de IA multi-herramientas que utiliza el ADK (Agent Development Kit) de Google para procesar y responder mensajes a través de Slack. Integra el modelo Gemini Pro para generar respuestas inteligentes y cuenta con características interactivas como reacciones emoji.

## Características

- Integración completa con Slack para recibir y responder mensajes
- Procesamiento de mensajes utilizando el modelo Gemini Pro
- Sistema de reacciones emoji para feedback visual
  - Reacciona con 👀 al recibir un mensaje
  - Cambia a ✅ después de procesar y responder
- Arquitectura extensible para agregar más herramientas
- Manejo robusto de errores y recuperación
- Sistema de logging detallado

## Requisitos

- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`
- Credenciales de Slack configuradas en el archivo `.env`
- Docker (opcional, para despliegue containerizado)

## Instalación

### Usando Docker (Recomendado)

```bash
docker pull alberth121484/rebeca-py:01.00.025
docker run -d --env-file .env alberth121484/rebeca-py:01.00.025
```

### Instalación Manual

1. Clonar el repositorio:
```bash
git clone [URL_DEL_REPOSITORIO]
cd rebeca
```

2. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar las variables de entorno en el archivo `.env`:
```env
SLACK_BOT_TOKEN=your_bot_token
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_APP_TOKEN=your_app_token
GEMINI_API_KEY=your_gemini_api_key
```

## Uso

### Con Docker

```bash
docker run -d --env-file .env alberth121484/rebeca-py:01.00.025
```

### Ejecución Local

```bash
python main.py
```

El agente se conectará a Slack y comenzará a escuchar mensajes. Responderá a:
- Mensajes directos (DMs)
- Menciones en canales (@rebeca)

## Estructura del Proyecto

```
├── main.py           # Punto de entrada de la aplicación
├── rebeca_agent.py   # Implementación principal del agente
├── slack_handler.py  # Manejador de eventos de Slack
├── message.py        # Clase Message para estructurar mensajes
├── requirements.txt  # Dependencias del proyecto
├── Dockerfile        # Configuración de Docker
├── .env              # Variables de entorno
└── tests/            # Pruebas unitarias
```

## Características Técnicas

### Sistema de Mensajería

- Clase `Message` para estructurar la comunicación
- Atributos: content, author, slack_channel, ts
- Manejo de timestamps para reacciones

### Integración con Slack

- Modo Socket para comunicación en tiempo real
- Sistema de reacciones emoji
- Manejo de eventos de mensajes y menciones
- Recuperación automática de errores

### Procesamiento con Gemini

- Integración con Gemini Pro para procesamiento de lenguaje natural
- Respuestas contextuales y coherentes
- Manejo de errores y reintentos

## Desarrollo

### Pruebas

Ejecutar las pruebas unitarias:
```bash
python -m pytest tests/
```

### Docker Build

Construir la imagen localmente:
```bash
docker build -t rebeca-py .
```

## Contribuir

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Distribuido bajo la licencia MIT. Ver `LICENSE` para más información.