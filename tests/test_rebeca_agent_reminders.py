import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from rebeca_agent import RebecaAgent

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv('SLACK_BOT_TOKEN', 'test-token')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    monkeypatch.setenv('BIGQUERY_PROJECT_ID', 'test-project')
    monkeypatch.setenv('BIGQUERY_DATASET', 'test-dataset')

@pytest.fixture
def agent(mock_env_vars):
    with patch('rebeca_agent.WebClient'), \
         patch('rebeca_agent.ReminderHandler'):
        agent = RebecaAgent()
        return agent

def test_parse_reminder_with_specific_time(agent):
    # Probar formato "a las HH:MM"
    content = "recuerdame llamar al jefe a las 14:00"
    message, time = agent._parse_reminder(content)
    
    assert message == "llamar al jefe"
    assert isinstance(time, datetime)
    assert time.hour == 14
    assert time.minute == 0

def test_parse_reminder_with_minutes(agent):
    # Probar formato "en X minutos"
    content = "recuerdame revisar documentos en 5 minutos"
    message, time = agent._parse_reminder(content)
    
    assert message == "revisar documentos"
    assert isinstance(time, datetime)
    
    # La hora debe ser aproximadamente la actual + 5 minutos
    now = datetime.now()
    diff = time - now
    assert 4 <= diff.total_seconds() / 60 <= 6  # Permitir un margen de error

def test_parse_reminder_with_hours(agent):
    # Probar formato "en X horas"
    content = "recuerdame enviar informe en 2 horas"
    message, time = agent._parse_reminder(content)
    
    assert message == "enviar informe"
    assert isinstance(time, datetime)
    
    # La hora debe ser aproximadamente la actual + 2 horas
    now = datetime.now()
    diff = time - now
    assert 1.9 <= diff.total_seconds() / 3600 <= 2.1  # Permitir un margen de error

def test_parse_reminder_invalid_format(agent):
    # Probar mensaje que no es un recordatorio
    content = "hola, ¿cómo estás?"
    message, time = agent._parse_reminder(content)
    
    assert message is None
    assert time is None

def test_process_reminder_message(agent):
    # Preparar un mensaje de recordatorio
    class Message:
        content = "recuerdame llamar al jefe a las 14:00"
        author = "U123456"
        slack_channel = "C123456"
        ts = "1234567890.123"
    
    # Mock para el reminder_handler
    mock_reminder = MagicMock(
        reminder_id="test-id",
        datetime="2024-03-17T14:00:00"
    )
    agent.reminder_handler.create_reminder.return_value = mock_reminder
    
    # Mock para el cliente de Slack
    agent.slack_client.reactions_add = MagicMock()
    agent.slack_client.reactions_remove = MagicMock()
    
    # Procesar el mensaje
    response = agent.process_message(Message())
    
    # Verificar que se creó el recordatorio
    agent.reminder_handler.create_reminder.assert_called_once()
    call_args = agent.reminder_handler.create_reminder.call_args[1]
    assert call_args['user_id'] == "U123456"
    assert call_args['message'] == "llamar al jefe"
    assert call_args['channel_id'] == "C123456"
    
    # Verificar la respuesta
    assert isinstance(response, dict)
    assert 'content' in response
    assert "¡Entendido!" in response['content']
    assert "14:00" in response['content']

def test_check_reminders(agent):
    # Preparar recordatorios de prueba
    mock_reminder = MagicMock(
        user_id="U123456",
        message="test reminder",
        channel_id="C123456",
        reminder_id="test-id"
    )
    agent.reminder_handler.get_pending_reminders.return_value = [mock_reminder]
    
    # Mock para el cliente de Slack
    agent.slack_client.chat_postMessage = MagicMock()
    
    # Ejecutar la verificación de recordatorios
    agent.check_reminders()
    
    # Verificar que se envió el mensaje
    agent.slack_client.chat_postMessage.assert_called_once_with(
        channel="C123456",
        text="<@U123456> ¡Recordatorio! test reminder"
    )
    
    # Verificar que se marcó como ejecutado
    agent.reminder_handler.mark_reminder_as_executed.assert_called_once_with("test-id")