# utils/rankings/loader.py

from __future__ import annotations

import datetime
from typing import Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_SHEETS, GOOGLE_SERVICE_ACCOUNT_FILE
from .models import RankingEntry


DATE_EPOCH = datetime.date(1899, 12, 30)  # Google Sheets serial date epoch


def _col_to_index(label: str) -> int:
    """Convert column label like 'A', 'Z', 'AA', 'AT' -> 0-based index."""
    label = label.upper()
    result = 0
    for ch in label:
        if not ('A' <= ch <= 'Z'):
            continue
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1  # zero-based


def _parse_sheet_date(value) -> Optional[datetime.date]:
    """Parse flexible date formats from Google Sheets.

    Supports:
    - Native serial numbers (UNFORMATTED_VALUE)
    - Strings like '1985/11/28', '1985-11-28'
    - Sentinel year 1000 for 'unknown year' style dates (e.g. '1000/11/00')
    """
    if value in (None, ""):
        return None

    # Serial number from Sheets
    if isinstance(value, (int, float)):
        try:
            return DATE_EPOCH + datetime.timedelta(days=int(value))
        except Exception:
            return None

    s = str(value).strip()
    if not s:
        return None

    # Normalize separators
    s = s.replace("-", "/")
    parts = s.split("/")
    if len(parts) != 3:
        return None

    try:
        year = int(parts[0])
        month = int(parts[1]) if parts[1] not in ("", "00") else 1
        day = int(parts[2]) if parts[2] not in ("", "00") else 1
        return datetime.date(year, month, day)
    except Exception:
        return None


class RankingsLoader:
    """Loads ranking data from the configured Google Sheet into RankingEntry objects."""

    def __init__(self) -> None:
        cfg = GOOGLE_SHEETS["rankings"]

        self.spreadsheet_id: str = cfg["spreadsheet_id"]
        self.sheet_name: str = cfg["sheet_name"]
        self.header_row: int = cfg["header_row"]
        self.data_row_start: int = cfg["data_row_start"]
        self.columns: Dict[str, str] = cfg["columns"]

        self.entries: List[RankingEntry] = []

        # Indexes used by commands
        self.by_name_lower: Dict[str, RankingEntry] = {}
        self.by_slug: Dict[str, RankingEntry] = {}
        self.by_rank: Dict[str, RankingEntry] = {}
        self.by_birth_year: Dict[int, List[RankingEntry]] = {}
        self.by_country: Dict[str, List[RankingEntry]] = {}
        self.by_state: Dict[str, List[RankingEntry]] = {}
        self.by_city: Dict[str, List[RankingEntry]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Fetch rows from Sheets and rebuild all indexes."""
        self.entries.clear()
        self.by_name_lower.clear()
        self.by_slug.clear()
        self.by_rank.clear()
        self.by_birth_year.clear()
        self.by_country.clear()
        self.by_state.clear()
        self.by_city.clear()

        creds = Credentials.from_service_account_file(
            str(GOOGLE_SERVICE_ACCOUNT_FILE),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        service = build("sheets", "v4", credentials=creds)

        # Fetch through column BZ (extended after notes column was added)
        range_end = "BZ"
        range_str = f"{self.sheet_name}!A{self.data_row_start}:{range_end}"

        result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_str,
            valueRenderOption="UNFORMATTED_VALUE",
            majorDimension="ROWS",
        ).execute()

        rows = result.get("values", []) or []
        for row in rows:
            entry = self._parse_row(row)
            if entry:
                self.entries.append(entry)
                self._index(entry)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_col(self, row: List, key: str):
        label = self.columns.get(key)
        if not label:
            return None
        idx = _col_to_index(label)
        if idx < 0 or idx >= len(row):
            return None
        return row[idx]

    def _get_col_by_letter(self, row: List, col_letter: str):
        """Get column value by letter directly (e.g., 'AB')."""
        idx = _col_to_index(col_letter)
        if idx < 0 or idx >= len(row):
            return None
        return row[idx]

    def _parse_row(self, row: List) -> Optional[RankingEntry]:
        name = self._get_col(row, "name")
        if not name:
            return None
        name = str(name).strip()
        if not name:
            return None

        # Group is required and numeric (1â€“8)
        group_raw = self._get_col(row, "group")
        try:
            group = int(group_raw)
        except Exception:
            return None

        # Rank: keep the raw string exactly as in the sheet.
        rank_val = self._get_col(row, "rank")
        rank_raw = str(rank_val).strip() if rank_val not in (None, "") else "?"

        # Birth / death dates
        birth_raw = self._get_col(row, "birthdate")
        birth_date = _parse_sheet_date(birth_raw)

        death_raw = self._get_col(row, "date_of_death")
        death_date = _parse_sheet_date(death_raw)

        # Place of birth
        pob_raw = self._get_col(row, "place_of_birth")
        birth_city = birth_state = birth_country = None
        if pob_raw:
            pob = str(pob_raw).strip()
            if pob:
                parts = [p.strip() for p in pob.split(",") if p.strip()]
                if len(parts) == 1:
                    birth_city = parts[0]
                elif len(parts) == 2:
                    birth_city, birth_country = parts
                elif len(parts) >= 3:
                    birth_city, birth_state, birth_country = parts[0], parts[1], parts[2]

        gender_raw = self._get_col(row, "gender")
        gender = str(gender_raw).strip() if gender_raw not in (None, "") else None

        slug_raw = self._get_col(row, "slug")
        slug = str(slug_raw).strip() if slug_raw not in (None, "") else None

        # Social media fields
        instagram = self._get_col_by_letter(row, "N")
        twitter = self._get_col_by_letter(row, "O")
        tiktok = self._get_col_by_letter(row, "R")

        # Physical description columns (columns AB through AO)
        physical_attrs = {
            "height": self._get_col_by_letter(row, "AB"),
            "build": self._get_col_by_letter(row, "AC"),
            "frame": self._get_col_by_letter(row, "AD"),
            "shoulders": self._get_col_by_letter(row, "AE"),
            "chest": self._get_col_by_letter(row, "AF"),
            "waist": self._get_col_by_letter(row, "AG"),
            "hips": self._get_col_by_letter(row, "AH"),
            "glutes": self._get_col_by_letter(row, "AI"),
            "leg_proportions": self._get_col_by_letter(row, "AJ"),
            "facial_shape": self._get_col_by_letter(row, "AK"),
            "eyes": self._get_col_by_letter(row, "AL"),
            "nose": self._get_col_by_letter(row, "AM"),
            "lips": self._get_col_by_letter(row, "AN"),
            "hair": self._get_col_by_letter(row, "AO"),
        }

        # Extra fields
        images_start = self._get_col(row, "images_start")
        images_end = self._get_col(row, "images_end")
        bluesky = self._get_col(row, "bluesky")

        extra = {
            "images_start": images_start,
            "images_end": images_end,
            "bluesky": bluesky,
            "instagram": instagram,
            "twitter": twitter,
            "tiktok": tiktok,
        }

        # Add physical attributes to extra dict (lowercase keys)
        extra.update(physical_attrs)

        entry = RankingEntry(
            name=name,
            slug=slug or name,
            group=group,
            rank_raw=rank_raw,
            birth_date=birth_date,
            death_date=death_date,
            birth_city=birth_city,
            birth_state=birth_state,
            birth_country=birth_country,
            known_for=None,
            known_for_label="Known For:",
            is_neverland=False,
            gender=gender,
            extra=extra,
        )
        
        # DON'T set as direct attributes - just keep in extra dict
        # Access them via entry.extra["build"], entry.extra["height"], etc.
        
        return entry

    def _index(self, e: RankingEntry) -> None:
        self.by_name_lower[e.name.lower()] = e
        if e.slug:
            self.by_slug[e.slug.lower()] = e
        if e.rank_raw:
            self.by_rank[e.rank_raw] = e

        if e.birth_date:
            self.by_birth_year.setdefault(e.birth_date.year, []).append(e)
        if e.birth_country:
            self.by_country.setdefault(e.birth_country, []).append(e)
        if e.birth_state:
            self.by_state.setdefault(e.birth_state, []).append(e)
        if e.birth_city:
            self.by_city.setdefault(e.birth_city, []).append(e)
