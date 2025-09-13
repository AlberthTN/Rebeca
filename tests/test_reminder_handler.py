import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from reminder_handler import ReminderHandler, Reminder
from google.cloud import bigquery

@pytest.fixture
def mock_bigquery():
    with patch('reminder_handler.bigquery.Client') as mock:
        client = mock.return_value
        # Configurar el mock para insert_rows_json
        client.insert_rows_json.return_value = []
        # Configurar el mock para query
        query_job = MagicMock()
        client.query.return_value = query_job
        yield mock

@pytest.fixture
def reminder_handler(mock_bigquery):
    handler = ReminderHandler('test-project', 'test-dataset')
    return handler

def test_create_reminder(reminder_handler):
    # Preparar datos de prueba
    user_id = "U123456"
    message = "llamar al jefe"
    channel_id = "C123456"
    reminder_datetime = datetime.now() + timedelta(hours=1)
    
    # Ejecutar la función
    reminder = reminder_handler.create_reminder(
        user_id=user_id,
        message=message,
        channel_id=channel_id,
        reminder_datetime=reminder_datetime
    )
    
    # Verificar resultados
    assert reminder.user_id == user_id
    assert reminder.message == message
    assert reminder.channel_id == channel_id
    assert reminder.datetime == reminder_datetime.isoformat()
    assert reminder.status == 'pending'
    assert reminder.reminder_type == 'once'
    assert reminder.reminder_id is not None

def test_save_to_bigquery(reminder_handler):
    # Preparar datos de prueba
    reminder = Reminder(
        user_id="U123456",
        message="test message",
        reminder_type="once",
        reminder_id="test-id",
        channel_id="C123456",
        datetime=datetime.now().isoformat(),
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Ejecutar la función
    reminder_handler._save_to_bigquery(reminder)
    
    # Verificar que se llamó a insert_rows_json
    reminder_handler.client.insert_rows_json.assert_called_once()
    
    # Verificar que se pasaron los datos correctos
    call_args = reminder_handler.client.insert_rows_json.call_args[0]
    assert "test-project.test-dataset.user_reminders" == call_args[0]
    assert len(call_args[1]) == 1  # Un solo registro
    row = call_args[1][0]
    assert row['reminder_id'] == reminder.reminder_id
    assert row['user_id'] == reminder.user_id
    assert row['message'] == reminder.message

def test_get_pending_reminders(reminder_handler):
    # Preparar datos de prueba
    mock_results = [
        MagicMock(
            user_id="U123456",
            message="test message",
            reminder_type="once",
            reminder_id="test-id",
            reminder_data='{"datetime":"2024-03-17T14:00:00","channel_id":"C123456","uuid":"test-id"}',
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    # Configurar el mock para query
    query_job = reminder_handler.client.query.return_value
    query_job.result.return_value = mock_results
    
    # Ejecutar la función
    reminders = reminder_handler.get_pending_reminders()
    
    # Verificar resultados
    assert len(reminders) == 1
    reminder = reminders[0]
    assert reminder.user_id == "U123456"
    assert reminder.message == "test message"
    assert reminder.channel_id == "C123456"
    assert reminder.status == "pending"

def test_mark_reminder_as_executed(reminder_handler):
    # Preparar datos
    reminder_id = "test-id"
    
    # Ejecutar la función
    reminder_handler.mark_reminder_as_executed(reminder_id)
    
    # Verificar que se llamó a query con los parámetros correctos
    reminder_handler.client.query.assert_called_once()
    call_args = reminder_handler.client.query.call_args
    
    # Verificar la consulta SQL
    sql = call_args[0][0]
    assert "UPDATE" in sql
    assert "SET status = 'executed'" in sql
    assert "WHERE reminder_id = @reminder_id" in sql
    
    # Verificar el job_config con los parámetros de la consulta
    job_config = call_args[1]['job_config']
    assert isinstance(job_config, bigquery.QueryJobConfig)
    assert len(job_config.query_parameters) == 1
    param = job_config.query_parameters[0]
    assert param.name == 'reminder_id'
    assert param.value == 'test-id'