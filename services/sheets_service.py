import gspread
import logging
import json
import os
from typing import List, Set, Tuple
from core.models import Transaction
from core.config import settings
from core.validators.duplicate_validator import generate_transaction_fingerprint


class SheetsService:
    def __init__(self, spreadsheet_name: str, worksheet_name: str = "Transactions"):
        try:
            # Check for production credentials from environment
            creds_env = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
            
            if creds_env:
                creds_dict = json.loads(creds_env)
                self.client = gspread.service_account_from_dict(creds_dict)
            else:
                # Fallback to local credential file for development
                self.client = gspread.service_account(filename=settings.SHEETS_CREDENTIALS)
            
            self.spreadsheet = self.client.open(spreadsheet_name)
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            logging.info(f"Successfully connected to spreadsheet: {spreadsheet_name}")
        except Exception as e:
            logging.error(f"Failed to initialize SheetsService: {e}")
            raise e

    def get_existing_rows(self) -> List[List[str]]:
        """
        Retrieves all data rows from the sheet, excluding the header row if present.
        """
        try:
            records = self.worksheet.get_all_values()
            return records[1:] if len(records) > 1 else []
        except Exception as exc:
            logging.error(f"Error fetching existing records from sheet: {exc}")
            return []

    def get_existing_fingerprints(self) -> Set[str]:
        """
        Builds a set of normalized deterministic fingerprints from existing sheet rows
        to enable bulletproof duplicate detection across formatted currency, dates, and text.
        """
        fingerprints: Set[str] = set()
        for row in self.get_existing_rows():
            if len(row) >= 3:
                date_val = row[0]
                tx_type = row[1] if len(row) > 1 else ""
                amount_val = row[2]
                source_val = row[3] if len(row) > 3 else ""
                dest_val = row[4] if len(row) > 4 else ""
                desc_val = row[7] if len(row) > 7 else ""

                fp = generate_transaction_fingerprint(
                    date_val=date_val,
                    amount_val=amount_val,
                    tx_type=tx_type,
                    source=source_val,
                    destination=dest_val,
                    description=desc_val,
                )
                fingerprints.add(fp)
        return fingerprints

    def append_raw_row(self, row_data: list):
        """Appends a single row directly into the Google Sheet."""
        self.worksheet.append_row(row_data, value_input_option="USER_ENTERED")

    def append_raw_rows(self, rows_data: list):
        """Appends multiple rows in a single batch call into the Google Sheet."""
        if rows_data:
            self.worksheet.append_rows(rows_data, value_input_option="USER_ENTERED")

    def append_transaction(self, transaction: Transaction) -> bool:
        """
        Appends a structured Transaction if not duplicate.
        Returns True if added, False if duplicate.
        """
        try:
            fingerprints = self.get_existing_fingerprints()
            tx_fp = generate_transaction_fingerprint(
                date_val=transaction.date,
                amount_val=transaction.amount,
                tx_type=transaction.transaction_type,
                source=transaction.source_account,
                destination=transaction.destination_account,
                description=transaction.description,
            )

            if tx_fp in fingerprints:
                logging.info(f"Duplicate detected, skipping: {tx_fp}")
                return False

            row_data = [
                transaction.date.isoformat(),
                transaction.transaction_type,
                transaction.amount,
                transaction.source_account or "",
                transaction.destination_account or "",
                transaction.category,
                transaction.subcategory,
                transaction.description,
            ]
            self.append_raw_row(row_data)
            logging.info(f"Transaction successfully recorded: ${transaction.amount} - {transaction.description}")
            return True
        except Exception as e:
            logging.error(f"Error appending row to Google Sheets: {e}")
            raise e

    def append_transactions(self, transactions: List[Transaction]) -> Tuple[int, int]:
        """
        Appends multiple transactions in batch, filtering out duplicates.
        Returns (added_count, duplicate_count).
        """
        try:
            fingerprints = self.get_existing_fingerprints()
            rows_to_insert = []
            duplicates = 0

            for tx in transactions:
                tx_fp = generate_transaction_fingerprint(
                    date_val=tx.date,
                    amount_val=tx.amount,
                    tx_type=tx.transaction_type,
                    source=tx.source_account,
                    destination=tx.destination_account,
                    description=tx.description,
                )

                if tx_fp in fingerprints:
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
                        tx.description,
                    ])
                    # Add to fingerprints to prevent duplicate items inside the same batch
                    fingerprints.add(tx_fp)

            if rows_to_insert:
                self.append_raw_rows(rows_to_insert)
                logging.info(f"Batch inserted {len(rows_to_insert)} transactions.")

            return len(rows_to_insert), duplicates
        except Exception as e:
            logging.error(f"Error appending rows in batch: {e}")
            raise e