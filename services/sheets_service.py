import gspread
import logging
import json
import os
from core.models import Transaction
from core.config import settings

class SheetsService:
    def __init__(self, spreadsheet_name: str, worksheet_name: str = "Transactions"):
        try:
            # Intentamos leer las credenciales desde una variable de entorno (Para Producción)
            creds_env = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
            
            if creds_env:
                creds_dict = json.loads(creds_env)
                self.client = gspread.service_account_from_dict(creds_dict)
            else:
                # Fallback: leemos el archivo local (Para Desarrollo)
                self.client = gspread.service_account(filename=settings.SHEETS_CREDENTIALS)
            
            self.spreadsheet = self.client.open(spreadsheet_name)
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            logging.info(f"Successfully connected to spreadsheet: {spreadsheet_name}")
        except Exception as e:
            logging.error(f"Failed to initialize SheetsService: {e}")
            raise e

    def _get_existing_signatures(self) -> set:
        """
        Retrieves existing transactions from the sheet and creates a unique signature
        for each to avoid duplicates: (date, amount, source_account).
        """
        try:
            records = self.worksheet.get_all_values()
            signatures = set()
            # Asumimos que la primera fila podría ser encabezado, iteramos todas
            for row in records[1:]:  # Omitimos header si existe
                if len(row) >= 4:
                    date_val = row[0]
                    amount_val = row[2]
                    source_val = row[3]
                    signatures.add(f"{date_val}_{amount_val}_{source_val}")
            return signatures
        except Exception as e:
            logging.error(f"Error fetching existing records: {e}")
            return set()

    def append_transaction(self, transaction: Transaction) -> bool:
        """
        Appends a structured Transaction object as a new row in the worksheet if it's not a duplicate.
        Returns True if added, False if it was a duplicate.
        """
        try:
            signatures = self._get_existing_signatures()
            signature = f"{transaction.date.isoformat()}_{transaction.amount}_{transaction.source_account or ''}"
            
            if signature in signatures:
                logging.info(f"Duplicate detected, skipping: {signature}")
                return False

            row_data = [
                transaction.date.isoformat(),
                transaction.transaction_type,
                transaction.amount,
                transaction.source_account or "",
                transaction.destination_account or "",
                transaction.category,
                transaction.subcategory,
                transaction.description
            ]
            self.worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            logging.info(f"Transaction successfully recorded: ${transaction.amount} - {transaction.description}")
            return True
        except Exception as e:
            logging.error(f"Error appending row to Google Sheets: {e}")
            raise e

    def append_transactions(self, transactions: list[Transaction]) -> tuple[int, int]:
        """
        Appends multiple transactions at once, filtering out duplicates.
        Returns (added_count, duplicate_count).
        """
        try:
            signatures = self._get_existing_signatures()
            rows_to_insert = []
            duplicates = 0
            
            for tx in transactions:
                signature = f"{tx.date.isoformat()}_{tx.amount}_{tx.source_account or ''}"
                if signature in signatures:
                    duplicates += 1
                else:
                    rows_to_insert.append([
                        tx.date.isoformat(),
                        tx.transaction_type,
                        tx.amount,
                        tx.source_account or "",
                        tx.destination_account or "",
                        tx.category,
                        tx.subcategory,
                        tx.description
                    ])
                    # Add to signatures to prevent duplicates within the same batch
                    signatures.add(signature)
            
            if rows_to_insert:
                self.worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED")
                logging.info(f"Batch inserted {len(rows_to_insert)} transactions.")
            
            return len(rows_to_insert), duplicates
        except Exception as e:
            logging.error(f"Error appending rows in batch: {e}")
            raise e