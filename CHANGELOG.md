# Changelog

## [1.1.0] - 2024-03-17

### Agregado
- Sistema de recordatorios integrado con BigQuery
  - Almacenamiento de recordatorios en tabla `neto-cloud.agente_rebeca.user_reminders`
  - Procesamiento de comandos de recordatorio en formato natural
  - Monitoreo automático de recordatorios pendientes
  - Notificaciones por Slack cuando se cumplen los recordatorios
- Integración con Google BigQuery para persistencia de datos

## [1.0.0] - 2024-03-17

### Agregado
- Integración con Slack
  - Procesamiento de mensajes directos y menciones
  - Reacciones con emojis para indicar estado del procesamiento
  - Manejo de timestamps para reacciones
- Procesamiento de lenguaje natural con Gemini Pro
  - Respuestas contextuales y coherentes
  - Manejo de errores y recuperación
- Arquitectura modular y extensible
  - Clases y módulos bien organizados
  - Manejo de configuración vía variables de entorno
- Documentación completa
  - README con instrucciones de instalación y uso
  - Licencia MIT
  - Estructura del proyecto y características técnicas