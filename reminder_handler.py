from dataclasses import dataclass
from datetime import datetime
import uuid
from google.cloud import bigquery
from typing import Optional, Dict
import json
import os
from google.oauth2 import service_account
import pytz

@dataclass
class Reminder:
    user_id: str
    message: str
    reminder_type: str  # 'once' for one-time reminders
    reminder_id: str
    channel_id: str
    datetime: str
    status: str = 'pending'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ReminderHandler:
    def __init__(self, project_id: str, dataset_id: str):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = 'user_reminders'
        self.history_table_id = 'user_reminders_history'
        
        # Configurar cliente con credenciales desde variable de entorno
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            self.client = bigquery.Client(
                project=project_id,
                credentials=credentials
            )
        else:
            self.client = bigquery.Client()
        
        # Crear tablas si no existen
        self._ensure_tables_exist()

    def create_reminder(self, user_id: str, message: str, channel_id: str, reminder_datetime: datetime) -> Reminder:
        reminder_id = str(uuid.uuid4())
        reminder = Reminder(
            user_id=user_id,
            message=message,
            reminder_type='once',
            reminder_id=reminder_id,
            channel_id=channel_id,
            datetime=reminder_datetime.isoformat(),
            created_at=datetime.now(pytz.timezone('America/Mexico_City')),
            updated_at=datetime.now(pytz.timezone('America/Mexico_City'))
        )
        
        self._save_to_bigquery(reminder)
        return reminder

    def _save_to_bigquery(self, reminder: Reminder) -> None:
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

        row = {
            'reminder_id': reminder.reminder_id,
            'slack_user_id': reminder.user_id,
            'title': reminder.message,
            'trigger_type': reminder.reminder_type,
            'trigger_params': json.dumps({'channel_id': reminder.channel_id, 'datetime': reminder.datetime}),
            'status': reminder.status,
            'created_at': datetime.now(pytz.timezone('America/Mexico_City')).isoformat()
        }

        errors = self.client.insert_rows_json(table_ref, [row])
        if errors:
            raise Exception(f'Error inserting reminder: {errors}')

    def get_pending_reminders(self) -> list[Reminder]:
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        history_table_ref = f"{self.project_id}.{self.dataset_id}.{self.history_table_id}"
        
        query = f"""
        WITH executed_reminders AS (
            SELECT DISTINCT reminder_id
            FROM `{history_table_ref}`
            WHERE status = 'executed'
        ),
        current_time AS (
            SELECT DATETIME(CURRENT_TIMESTAMP(), 'America/Mexico_City') as cdmx_time
        ),
        reminder_times AS (
            SELECT r.*,
                   PARSE_DATETIME('%Y-%m-%dT%H:%M:%S', JSON_EXTRACT_SCALAR(r.trigger_params, '$.datetime')) as reminder_time
            FROM `{table_ref}` r
        )
        SELECT r.*
        FROM reminder_times r
        LEFT JOIN executed_reminders e ON r.reminder_id = e.reminder_id
        CROSS JOIN current_time ct
        WHERE e.reminder_id IS NULL
        AND r.status = 'pending'
        AND ABS(TIMESTAMP_DIFF(
            TIMESTAMP(r.reminder_time),
            TIMESTAMP(ct.cdmx_time),
            SECOND
        )) <= 40
        """
        
        query_job = self.client.query(query)
        results = query_job.result()

        reminders = []
        for row in results:
            trigger_params = json.loads(row.trigger_params)
            reminder = Reminder(
                user_id=row.slack_user_id,
                message=row.title,
                reminder_type=row.trigger_type,
                reminder_id=row.reminder_id,
                channel_id=trigger_params['channel_id'],
                datetime=trigger_params['datetime'],
                status=row.status,
                created_at=row.created_at,
                updated_at=None
            )
            reminders.append(reminder)

        return reminders

    def mark_reminder_as_executed(self, reminder_id: str) -> None:
        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        history_table_ref = f"{self.project_id}.{self.dataset_id}.{self.history_table_id}"
        
        # Obtener el recordatorio pendiente
        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE reminder_id = @reminder_id
        AND status = 'pending'
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("reminder_id", "STRING", reminder_id)
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            raise Exception(f'Pending reminder {reminder_id} not found')
            
        current_reminder = results[0]
        
        # Insertar el estado ejecutado en la tabla de historial
        row = {
            'reminder_id': current_reminder.reminder_id,
            'slack_user_id': current_reminder.slack_user_id,
            'title': current_reminder.title,
            'trigger_type': current_reminder.trigger_type,
            'trigger_params': current_reminder.trigger_params,
            'status': 'executed',
            'created_at': datetime.now(pytz.timezone('America/Mexico_City')).isoformat(),
            'executed_at': datetime.now(pytz.timezone('America/Mexico_City')).isoformat()
        }

        errors = self.client.insert_rows_json(history_table_ref, [row])
        if errors:
            raise Exception(f'Error updating reminder status: {errors}')
            
    def _ensure_tables_exist(self) -> None:
        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        table_ref = f"{dataset_ref}.{self.table_id}"
        history_table_ref = f"{dataset_ref}.{self.history_table_id}"
        
        # Crear dataset si no existe
        try:
            self.client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "us-central1"
            self.client.create_dataset(dataset, exists_ok=True)
        
        # Esquema para la tabla principal
        main_schema = [
            bigquery.SchemaField("reminder_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("slack_user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trigger_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trigger_params", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED")
        ]
        
        # Esquema para la tabla de historial
        history_schema = [
            bigquery.SchemaField("reminder_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("slack_user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trigger_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("trigger_params", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("executed_at", "TIMESTAMP", mode="REQUIRED")
        ]
        
        # Crear tabla principal si no existe
        try:
            self.client.get_table(table_ref)
        except Exception:
            table = bigquery.Table(table_ref, schema=main_schema)
            self.client.create_table(table, exists_ok=True)
        
        # Crear tabla de historial si no existe
        try:
            self.client.get_table(history_table_ref)
        except Exception:
            history_table = bigquery.Table(history_table_ref, schema=history_schema)
            self.client.create_table(history_table, exists_ok=True)