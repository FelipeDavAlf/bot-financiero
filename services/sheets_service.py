import gspread
import logging
from core.models import Transaction
from core.config import settings

class SheetsService:
    """
    Service responsible for interacting with the Google Sheets API.
    
    This class handles authentication via a Google Service Account and manages
    the appending of validated Transaction records into a specific spreadsheet.
    """

    def __init__(self, spreadsheet_name: str, worksheet_name: str = "Transactions"):
        """
        Initializes the SheetsService by authenticating and opening the target worksheet.

        Args:
            spreadsheet_name (str): The exact title of the Google Spreadsheet.
            worksheet_name (str): The specific tab name within the spreadsheet. 
                Defaults to "Transactions".
        """
        try:
            # Authenticate using the credentials JSON file path from settings
            self.client = gspread.service_account(filename=settings.SHEETS_CREDENTIALS)
            
            # Open the spreadsheet and select the specific worksheet
            self.spreadsheet = self.client.open(spreadsheet_name)
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            logging.info(f"Successfully connected to spreadsheet: {spreadsheet_name}")
        except Exception as e:
            logging.error(f"Failed to initialize SheetsService: {e}")
            raise e

    def append_transaction(self, transaction: Transaction) -> None:
        """
        Appends a structured Transaction object as a new row in the worksheet.

        The order of the columns matches the relational architecture designed
        for downstream analytics and data modeling.

        Args:
            transaction (Transaction): The validated Pydantic model containing 
                the financial movement details.

        Raises:
            Exception: If the append operation fails due to API or connection issues.
        """
        try:
            # Format the row data exactly matching the Pydantic schema
            row_data = [
                transaction.date.isoformat(),
                transaction.transaction_type,
                transaction.amount,
                transaction.source_account or "",
                transaction.destination_account or "",
                transaction.category,
                transaction.description
            ]
            
            # Append the row to the end of the sheet, ensuring values are parsed correctly
            self.worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            logging.info(f"Transaction successfully recorded: ${transaction.amount} - {transaction.description}")
        except Exception as e:
            logging.error(f"Error appending row to Google Sheets: {e}")
            raise e