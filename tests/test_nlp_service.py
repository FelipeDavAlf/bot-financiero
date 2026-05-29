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
    assert transaction.amount == 150.0
    assert transaction.category == "Comida"
    assert transaction.transaction_type == "Gasto"
    assert transaction.source_account == "Tarjeta Débito"