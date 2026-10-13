from unittest.mock import patch, MagicMock
from services.nlp_service import NLPService

# Interceptamos el cliente de Gemini para que no haga llamadas reales a internet
@patch('services.nlp_service.genai.Client')
def test_process_message_success(mock_genai_client_class):
    # 1. Preparamos nuestro "Gemini Falso"
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    
    # Este es el JSON que simula la respuesta de la IA
    mock_response.text = """
    {
        "date": "2026-05-28", 
        "transaction_type": "Gasto", 
        "amount": 150.0, 
        "source_account": "Tarjeta Débito", 
        "destination_account": null, 
        "category": "Comida", 
        "subcategory": "Pizza",
        "description": "Pizza"
    }
    """
    
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client_class.return_value = mock_client_instance

    # 2. Ejecutamos tu servicio real
    nlp = NLPService()
    transaction = nlp.message_processor("Gasté 150 en una pizza con tarjeta de débito")

    # 3. Validamos que el JSON se haya convertido perfectamente a tu Pydantic model
    assert transaction is not None
    assert transaction.amount == 150.0
    assert transaction.category == "Comida"
    assert transaction.transaction_type == "Gasto"
    assert transaction.source_account == "Tarjeta Débito"


@patch('services.nlp_service.genai.Client')
def test_process_message_non_transaction(mock_genai_client_class):
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"is_transaction": false}'
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client_class.return_value = mock_client_instance

    nlp = NLPService()
    transaction = nlp.message_processor("Hola, ¿cómo estás hoy?")

    assert transaction is None


def test_greeting_intent_detection():
    from services.bot_messages import is_greeting_or_help_intent

    assert is_greeting_or_help_intent("Hola")
    assert is_greeting_or_help_intent("buenos días")
    assert is_greeting_or_help_intent("ayuda")
    assert is_greeting_or_help_intent("info")
    assert not is_greeting_or_help_intent("Gasté 100 pesos en tacos")
    assert not is_greeting_or_help_intent("Pagué la luz")


def test_sanitize_transaction_data_relative_dates():
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    raw = {
        "date": "ayer",
        "transaction_type": "gasto",
        "amount": "222 pesos",
        "source_account": "tarjeta de rappi",
        "category": "Vivienda y Servicios",
        "description": "Estantes baño"
    }
    clean = NLPService._sanitize_transaction_data(raw)
    assert clean["date"] == yesterday
    assert clean["transaction_type"] == "Gasto"
    assert clean["amount"] == 222.0
    assert clean["source_account"] == "Tarjeta Crédito Rappi"


@patch('services.nlp_service.genai.Client')
def test_process_message_with_relative_date_and_raw_amount(mock_genai_client_class):
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """
    {
        "date": "ayer",
        "transaction_type": "gasto",
        "amount": "$222.00 pesos",
        "source_account": "tarjeta rappi",
        "destination_account": null,
        "category": "Vivienda y Servicios",
        "subcategory": "Estantes baño",
        "description": "Estantes para baño"
    }
    """
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client_class.return_value = mock_client_instance

    nlp = NLPService()
    transaction = nlp.message_processor("Gaste 222 pesos en estantes para baño con tarjeta de rappi ayer")

    assert transaction is not None
    assert transaction.date.isoformat() == yesterday
    assert transaction.transaction_type == "Gasto"
    assert transaction.amount == 222.0
    assert transaction.source_account == "Tarjeta Crédito Rappi"