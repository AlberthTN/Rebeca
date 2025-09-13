import os
import json
import pytest
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from reminder_handler import ReminderHandler

@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv()
    # Verificar que las variables de entorno necesarias estén configuradas
    required_vars = [
        'BIGQUERY_PROJECT_ID',
        'BIGQUERY_DATASET',
        'GOOGLE_APPLICATION_CREDENTIALS_JSON'
    ]
    for var in required_vars:
        assert os.getenv(var) is not None, f"{var} no está configurado"

@pytest.fixture(scope="function")
def test_tables(request):
    project_id = os.getenv('BIGQUERY_PROJECT_ID')
    dataset_id = os.getenv('BIGQUERY_DATASET')
    table_id = f"test_reminders_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    history_table_id = f"test_reminders_history_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    # Configurar cliente con credenciales desde variable de entorno
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    client = bigquery.Client(project=project_id, credentials=credentials)
    
    # Crear tabla temporal para pruebas
    schema = [
        bigquery.SchemaField("reminder_id", "STRING"),
        bigquery.SchemaField("slack_user_id", "STRING"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("trigger_type", "STRING"),
        bigquery.SchemaField("trigger_params", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("created_at", "TIMESTAMP"),
        bigquery.SchemaField("executed_at", "TIMESTAMP")
    ]
    
    # Crear tabla principal
    table = bigquery.Table(f"{project_id}.{dataset_id}.{table_id}", schema=schema)
    table = client.create_table(table)
    
    # Crear tabla de historial
    history_table = bigquery.Table(f"{project_id}.{dataset_id}.{history_table_id}", schema=schema)
    history_table = client.create_table(history_table)
    
    def cleanup():
        # Eliminar tablas temporales después de la prueba
        client.delete_table(table)
        client.delete_table(history_table)
    
    request.addfinalizer(cleanup)
    return table_id, history_table_id

@pytest.mark.integration
def test_reminder_integration(test_tables):
    project_id = os.getenv('BIGQUERY_PROJECT_ID')
    dataset_id = os.getenv('BIGQUERY_DATASET')
    table_id, history_table_id = test_tables
    
    # Crear instancia del manejador de recordatorios con las tablas temporales
    handler = ReminderHandler(project_id, dataset_id)
    handler.table_id = table_id
    handler.history_table_id = history_table_id
    
    # Crear un recordatorio de prueba
    reminder_datetime = datetime(2024, 12, 31, 23, 59, 59)
    reminder = handler.create_reminder(
        user_id="U123",
        message="Recordatorio de prueba",
        channel_id="C123",
        reminder_datetime=reminder_datetime
    )
    
    # Verificar que se puede recuperar
    pending = handler.get_pending_reminders()
    assert any(r.reminder_id == reminder.reminder_id for r in pending), \
        "El recordatorio no se encontró en la lista de pendientes"
    
    # Marcar como ejecutado
    handler.mark_reminder_as_executed(reminder.reminder_id)
    
    # Verificar que ya no está pendiente
    pending_after = handler.get_pending_reminders()
    assert all(r.reminder_id != reminder.reminder_id for r in pending_after), \
        "El recordatorio sigue apareciendo como pendiente después de marcarlo como ejecutado"