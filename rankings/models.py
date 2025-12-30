# utils/rankings/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional, Tuple


@dataclass(slots=True)
class RankingEntry:
    """
    Core representation of a single ranking entry.

    This object mirrors the Rankings Google Sheet closely and provides:
    - rank display logic
    - stable sorting
    - age calculations
    - birthplace formatting

    It is intentionally lightweight and data-oriented.
    """

    # ------------------------------------------------------------
    # Required Identity Fields
    # ------------------------------------------------------------

    name: str
    slug: str
    group: int
    rank_raw: str

    # ------------------------------------------------------------
    # Birth / Death Info
    # ------------------------------------------------------------

    birth_date: Optional[date] = None
    death_date: Optional[date] = None

    # ------------------------------------------------------------
    # Birthplace Breakdown
    # ------------------------------------------------------------

    birth_city: Optional[str] = None
    birth_state: Optional[str] = None
    birth_country: Optional[str] = None

    # ------------------------------------------------------------
    # Narrative / Presentation
    # ------------------------------------------------------------

    known_for: Optional[str] = None
    known_for_label: str = "Known For:"
    is_neverland: bool = False

    # ------------------------------------------------------------
    # Other Metadata
    # ------------------------------------------------------------

    gender: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    # ============================================================
    # Rank logic
    # ============================================================

    @property
    def is_group_one(self) -> bool:
        """True if this entry belongs to Group 1."""
        return self.group == 1

    @property
    def letter_rank(self) -> Optional[str]:
        """
        Letter rank (A, B, C...) for Group 1 entries.

        Returns None for non-Group-1 entries or invalid values.
        """
        if not self.is_group_one:
            return None

        raw = self.rank_raw.strip().upper()
        return raw or None

    @property
    def numeric_rank(self) -> Optional[int]:
        """
        Numeric rank for Group 2+ entries.

        Returns None if rank_raw is not a valid integer.
        """
        try:
            return int(self.rank_raw)
        except (TypeError, ValueError):
            return None

    @property
    def display_rank_for_title(self) -> str:
        """
        Rank token used in profile card titles.
        """
        if self.is_group_one and self.letter_rank:
            return self.letter_rank
        if self.numeric_rank is not None:
            return f"#{self.numeric_rank}"
        return str(self.rank_raw)

    @property
    def display_rank_for_list(self) -> str:
        """
        Rank token used in list embeds.
        """
        if self.is_group_one and self.letter_rank:
            return f"#{self.letter_rank}"
        if self.numeric_rank is not None:
            return f"#{self.numeric_rank}"
        return f"#{self.rank_raw}"

    @property
    def sort_key_overall(self) -> Tuple[int, int]:
        """
        Stable, deterministic sorting key.

        Ordering:
        - Group ASC
        - Group 1: letter rank A=1, B=2, ...
        - Group 2+: numeric rank ASC
        """
        if self.is_group_one:
            if self.letter_rank and "A" <= self.letter_rank <= "Z":
                order = ord(self.letter_rank) - ord("A") + 1
            else:
                order = 99
        else:
            order = self.numeric_rank if self.numeric_rank is not None else 999_999

        return (self.group, order)

    @property
    def sort_key_rank_only(self) -> Tuple[int, int]:
        """
        True rank-only sorting key.

        Rules:
        - Group 1 → alphabetic rank (A, B, C...)
        - Groups 2+ → numeric rank
        - Group number itself is NOT a ranking factor
        """
        if self.is_group_one:
            if self.letter_rank and "A" <= self.letter_rank <= "Z":
                order = ord(self.letter_rank) - ord("A") + 1
            else:
                order = 99
            return (0, order)

        order = self.numeric_rank if self.numeric_rank is not None else 999_999
        return (1, order)


    # ============================================================
    # Birthplace + Age logic
    # ============================================================

    @property
    def birthplace_display(self) -> str:
        """
        Human-readable birthplace string.
        """
        parts = [
            p for p in (
                self.birth_city,
                self.birth_state,
                self.birth_country,
            )
            if p
        ]
        return ", ".join(parts)

    def age_on(self, on_date: date) -> Optional[int]:
        """
        Age on a given date.

        If deceased before `on_date`, age is calculated at death.
        """
        if not self.birth_date:
            return None

        reference = (
            self.death_date
            if self.death_date and self.death_date <= on_date
            else on_date
        )

        years = reference.year - self.birth_date.year
        if (reference.month, reference.day) < (
            self.birth_date.month,
            self.birth_date.day,
        ):
            years -= 1

        return years

    def hypothetical_age_on(self, on_date: date) -> Optional[int]:
        """
        Age on a given date, ignoring death date.
        """
        if not self.birth_date:
            return None

        years = on_date.year - self.birth_date.year
        if (on_date.month, on_date.day) < (
            self.birth_date.month,
            self.birth_date.day,
        ):
            years -= 1

        return years

    @property
    def is_deceased(self) -> bool:
        """True if this entry has a recorded death date."""
        return self.death_date is not None
