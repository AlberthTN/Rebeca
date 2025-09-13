import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from slack_sdk.errors import SlackApiError
import google.generativeai as genai
from google.adk import Agent
from google.adk.tools import FunctionTool
from rebeca_agent import RebecaAgent
from dataclasses import dataclass

@dataclass
class Message:
    content: str
    slack_channel: str = None

@pytest.fixture
def mock_env_vars():
    with patch.dict(os.environ, {
        'SLACK_BOT_TOKEN': 'test-token',
        'GEMINI_API_KEY': 'test-api-key'
    }):
        yield

@pytest.fixture
def agent(mock_env_vars):
    return RebecaAgent()

def test_agent_initialization(agent):
    assert agent is not None
    assert agent.slack_client is not None
    assert agent.basic_message_tool is not None
    assert isinstance(agent.basic_message_tool, FunctionTool)

@pytest.mark.asyncio
async def test_process_with_gemini(agent):
    # Preparar mensaje de prueba
    test_message = {'content': 'Hola, ¿cómo estás?'}
    
    # Simular respuesta de Gemini
    mock_response = Mock()
    mock_response.text = '¡Hola! Estoy bien, ¿y tú?'

    # Mockear el modelo de Gemini
    mock_model = Mock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch.object(genai, 'GenerativeModel', return_value=mock_model):
        response = await agent.process_with_gemini(test_message)

    # Verificar que se llamó al modelo y se recibió la respuesta esperada
    mock_model.generate_content_async.assert_called_once_with(test_message['content'])
    assert response['content'] == '¡Hola! Estoy bien, ¿y tú?'

@pytest.mark.asyncio
async def test_process_message(agent):
    # Preparar mensaje de prueba
    test_message = {'content': 'Hola, ¿cómo estás?'}
    
    # Simular respuesta del modelo
    mock_response = {'content': '¡Hola! Estoy bien, ¿y tú?'}
    agent.basic_message_tool.execute = Mock(return_value=mock_response)
    
    # Ejecutar el procesamiento del mensaje
    response = await agent.process_message(test_message)
    
    # Verificar que se llamó al modelo y se recibió la respuesta esperada
    agent.basic_message_tool.execute.assert_called_once_with(test_message)
    assert response['content'] == '¡Hola! Estoy bien, ¿y tú?'

@pytest.mark.asyncio
async def test_process_slack_message(agent):
    # Preparar mensaje de Slack
    test_message = Message(content='Hola desde Slack')
    test_message.slack_channel = 'test-channel'
    
    # Simular respuesta del modelo
    mock_response = {'content': '¡Hola! Te respondo en Slack'}
    agent.basic_message_tool.execute = Mock(return_value=mock_response)
    
    # Simular envío exitoso a Slack
    agent.slack_client.chat_postMessage = Mock()
    
    # Ejecutar el procesamiento del mensaje
    response = await agent.process_message(test_message)
    
    # Verificar que se llamó a Slack con los parámetros correctos
    agent.slack_client.chat_postMessage.assert_called_once_with(
        channel='test-channel',
        text='¡Hola! Te respondo en Slack'
    )

@pytest.mark.asyncio
async def test_slack_error_handling(agent):
    # Preparar mensaje de Slack
    test_message = {'content': 'Mensaje que generará error', 'slack_channel': 'test-channel'}
    
    # Simular respuesta del modelo
    mock_response = {'content': 'Respuesta que generará error'}
    agent.basic_message_tool.execute = Mock(return_value=mock_response)
    
    # Simular error de Slack
    error_response = {'error': 'channel_not_found'}
    agent.slack_client.chat_postMessage = Mock(
        side_effect=SlackApiError('Error', error_response)
    )
    
    # Ejecutar el procesamiento del mensaje y verificar que no se lance excepción
    response = await agent.process_message(test_message)
    assert response['content'] == 'Respuesta que generará error'