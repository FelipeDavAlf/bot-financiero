from unittest.mock import patch, MagicMock
from datetime import date
from core.models import Transaction
from services.sheets_service import SheetsService

@patch('services.sheets_service.gspread.service_account')
@patch('services.sheets_service.os.getenv')
def test_append_transaction_success(mock_getenv, mock_service_account):
    # Simulamos que NO estamos en Koyeb/Render, sino usando el archivo local
    mock_getenv.return_value = None 
    
    # Preparamos el Excel Falso
    mock_client = MagicMock()
    mock_sheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_client.open.return_value = mock_sheet
    mock_sheet.worksheet.return_value = mock_worksheet
    mock_service_account.return_value = mock_client

    # Inicializamos el servicio
    sheets_service = SheetsService(spreadsheet_name="Fake Sheet")

    # Creamos una transacción de prueba
    transaction = Transaction(
        date=date(2026, 5, 28),
        transaction_type="Gasto",
        amount=100.0,
        category="Transporte",
        description="Uber"
    )

    # Ejecutamos el método a probar
    sheets_service.append_transaction(transaction)

    # Validamos que se haya llamado al método append_row de gspread exactamente 1 vez
    assert mock_worksheet.append_row.called
    assert mock_worksheet.append_row.call_count == 1