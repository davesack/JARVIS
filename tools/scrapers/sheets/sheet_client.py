"""
SheetClient for Arena scrapers.

Provides methods for reading and writing to Google Sheets.
"""

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path
from typing import List, Optional
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config


class SheetClient:
    """Google Sheets API client."""
    
    def __init__(self):
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self.service = build("sheets", "v4", credentials=creds)
    
    def read_column(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        column: str,
    ) -> List[str]:
        """Read a single column from a sheet."""
        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{column}:{column}",
            )
            .execute()
        )
        values = result.get("values", [])
        return [row[0] if row else "" for row in values]
    
    def read_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        start_row: Optional[int] = None,
        end_row: Optional[int] = None,
    ) -> List[List[str]]:
        """Read all rows from a sheet."""
        range_str = sheet_name
        if start_row and end_row:
            range_str = f"{sheet_name}!A{start_row}:ZZ{end_row}"
        elif start_row:
            range_str = f"{sheet_name}!A{start_row}:ZZ"
        
        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range_str,
            )
            .execute()
        )
        return result.get("values", [])
    
    def append_rows(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        rows: List[List],
    ):
        """Append multiple rows to a sheet."""
        self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
    
    def update_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        values: List,
    ):
        """Update a specific row."""
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A{row_number}:ZZ{row_number}",
            valueInputOption="RAW",
            body={"values": [values]},
        ).execute()
