# utils/rankings/fun_facts.py

from __future__ import annotations

import random
import re
import math
import datetime
from typing import Iterable, List, Optional, Set, Callable, Tuple

from .models import RankingEntry

# ============================================================
# PRONOUNS
# ============================================================

def _pronouns(entry: RankingEntry) -> tuple[str, str, str]:
    """
    Returns (subject, object, possessive).
    """
    gender = getattr(entry, "gender", None)
    if not isinstance(gender, str):
        return ("they", "them", "their")

    g = gender.strip().upper()
    if g.startswith("F"):
        return ("she", "her", "her")
    if g.startswith("M"):
        return ("he", "him", "his")
    return ("they", "them", "their")


# ============================================================
# SAFE ATTRIBUTE ACCESS
# ============================================================

def _get(entry: RankingEntry, key: str) -> Optional[str]:
    val = getattr(entry, key, None)
    if isinstance(val, str):
        val = val.strip()
        return val or None
    return val


# ============================================================
# RANK SORTING / POSITION
# ============================================================

def _sort_key(e: RankingEntry) -> tuple[int, str]:
    """
    Global consistent sort: numeric rank first, then name.
    """
    num = getattr(e, "numeric_rank", None)
    if num is None:
        num = 10_000
    return (num, e.name)


def _cohort(entries: Iterable[RankingEntry], pred: Callable[[RankingEntry], bool]) -> list[RankingEntry]:
    return [e for e in entries if pred(e)]


def _position(entry: RankingEntry, cohort: list[RankingEntry]) -> Optional[tuple[int, int]]:
    if not cohort or entry not in cohort:
        return None
    ordered = sorted(cohort, key=_sort_key)
    return ordered.index(entry) + 1, len(ordered)


# ============================================================
# PERCENT LANGUAGE (HIGH VARIETY)
# ============================================================

_PERCENT_TEMPLATES = [
    "placing {subj} comfortably in the top {pct}%",
    "which puts {obj} ahead of roughly {pct}% of the field",
    "good for about the top {pct}% overall",
    "landing {obj} solidly within the top {pct}%",
    "putting {obj} among the top {pct}% of everyone listed",
    "meaning {subj} outperforms nearly {pct}% of the rankings",
]

def _percent_phrase(pos: int, total: int, subj: str, obj: str) -> str:
    if total < 15:
        return ""

    pct = int(round((pos / total) * 100))
    if pct >= 75:
        return ""

    # round to nearest 5
    pct = int(round(pct / 5) * 5)
    tpl = random.choice(_PERCENT_TEMPLATES)
    return ", " + tpl.format(subj=subj, obj=obj, pct=pct)


# ============================================================
# AGE HELPERS
# ============================================================

def _age_on(e: RankingEntry, today: datetime.date) -> Optional[int]:
    if not e.birth_date or e.birth_date.year == 1000:
        return None
    age = today.year - e.birth_date.year
    if (today.month, today.day) < (e.birth_date.month, e.birth_date.day):
        age -= 1
    return age


def _age_bucket(age: int) -> Optional[str]:
    if age < 20:
        return None
    if age < 30:
        return "20s"
    if age < 40:
        return "30s"
    if age < 50:
        return "40s"
    return "50+"


# ============================================================
# GEOGRAPHY NORMALIZATION
# ============================================================

def _geo_label(e: RankingEntry) -> Optional[str]:
    """
    City + State > State > Country
    """
    city = _get(e, "birth_city")
    state = _get(e, "birth_state")
    country = _get(e, "birth_country")

    if city and state:
        return f"{city}, {state}"
    if state:
        return state
    if country:
        return country
    return None


# ============================================================
# HEIGHT / WEIGHT PARSING
# ============================================================

def _parse_height_inches(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    m = re.search(r"(\d)'\s*(\d{1,2})", raw)
    if not m:
        return None
    return int(m.group(1)) * 12 + int(m.group(2))


def _height_bucket(inches: int) -> str:
    if inches < 65:
        return "under 5'5\""
    if inches <= 68:
        return "around average height"
    return "over 5'8\""


def _parse_weight(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    m = re.search(r"(\d{2,3})", raw)
    if not m:
        return None
    return int(m.group(1))


def _weight_bucket(lbs: int) -> str:
    if lbs < 140:
        return "under 140 lbs"
    if lbs <= 165:
        return "mid-range weight"
    return "over 165 lbs"


# ============================================================
# MEASUREMENTS
# ============================================================

def _parse_measurements(raw: Optional[str]) -> Optional[tuple[int, int, int]]:
    if not raw:
        return None
    m = re.search(r"(\d{2})\D+(\d{2})\D+(\d{2})", raw)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


# ============================================================
# TEXT VARIANTS (OPENERS)
# ============================================================

_OPENERS = [
    "Among everyone",
    "Looking at everyone",
    "Compared to all others",
    "Within the full rankings",
    "Across the entire list",
]

def _open() -> str:
    return random.choice(_OPENERS)


# ============================================================
# COHORT REGISTRATION
# ============================================================

Cohort = Tuple[
    str,                                    # category id
    Callable[[RankingEntry], bool],         # predicate
    List[Callable[[int, int], str]]         # sentence formatters
]


def _rank_sentence(
    pos: int,
    total: int,
    entry: RankingEntry,
    subj: str,
    obj: str,
    templates: list[str],
) -> str:
    base = random.choice(templates).format(
        name=entry.name,
        subj=subj,
        obj=obj,
        pos=pos,
        total=total,
    )
    return base + _percent_phrase(pos, total, subj, obj)


# ============================================================
# TEMPORAL COHORTS
# ============================================================

def temporal_cohorts(
    entry: RankingEntry,
    all_entries: list[RankingEntry],
    today: Optional[datetime.date],
    subj: str,
    obj: str,
) -> list[Cohort]:

    cohorts: list[Cohort] = []

    # ---- birth year ----
    if entry.birth_date and entry.birth_date.year not in (None, 1000):
        year = entry.birth_date.year

        def pred_year(e: RankingEntry):
            return e.birth_date and e.birth_date.year == year

        cohorts.append((
            "birth_year",
            pred_year,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among people born in {year}, {{name}} ranks #{{pos}} of {{total}}",
                        f"Looking only at {year} births, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {year} birth cohort, {{name}} holds rank #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- birth decade ----
    if entry.birth_date and entry.birth_date.year not in (None, 1000):
        decade = (entry.birth_date.year // 10) * 10

        def pred_decade(e: RankingEntry):
            return e.birth_date and (e.birth_date.year // 10) * 10 == decade

        cohorts.append((
            "birth_decade",
            pred_decade,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"In the {decade}s generation, {{name}} ranks #{{pos}} of {{total}}",
                        f"Among all {decade}s births, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {decade}s cohort, {{name}} sits at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- birth month ----
    if entry.birth_date:
        month = entry.birth_date.month
        month_name = entry.birth_date.strftime("%B")

        def pred_month(e: RankingEntry):
            return e.birth_date and e.birth_date.month == month

        cohorts.append((
            "birth_month",
            pred_month,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among everyone born in {month_name}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For {month_name} birthdays, {{name}} lands at #{{pos}} out of {{total}}",
                        f"Within the {month_name}-born group, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- birth day of month ----
    if entry.birth_date:
        day = entry.birth_date.day
        suffix = "th" if 11 <= day <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")

        def pred_day(e: RankingEntry):
            return e.birth_date and e.birth_date.day == day

        cohorts.append((
            "birth_day",
            pred_day,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those born on the {day}{suffix}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For {day}{suffix}-of-the-month birthdays, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {day}{suffix} birthday cohort, {{name}} sits at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- born before / after 1995 ----
    if entry.birth_date and entry.birth_date.year not in (None, 1000):
        pivot = 1995
        label = "born before 1995" if entry.birth_date.year < pivot else "born after 1995"

        def pred_pivot(e: RankingEntry):
            return e.birth_date and (
                e.birth_date.year < pivot if entry.birth_date.year < pivot else e.birth_date.year >= pivot
            )

        cohorts.append((
            "birth_era",
            pred_pivot,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those {label}, {{name}} ranks #{{pos}} of {{total}}",
                        f"Looking only at people {label}, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the group {label}, {{name}} holds #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- age bucket ----
    if today:
        age = _age_on(entry, today)
        if age is not None:
            bucket = _age_bucket(age)

            def pred_age(e: RankingEntry):
                ea = _age_on(e, today)
                return ea is not None and _age_bucket(ea) == bucket

            cohorts.append((
                "age_bucket",
                pred_age,
                [
                    lambda p, t: _rank_sentence(
                        p, t, entry, subj, obj,
                        [
                            f"Among people in their {bucket}, {{name}} ranks #{{pos}} of {{total}}",
                            f"Within the {bucket} age group, {{name}} places #{{pos}} out of {{total}}",
                            f"For those currently in their {bucket}, {{name}} comes in at #{{pos}} of {{total}}",
                        ],
                    )
                ],
            ))

    return cohorts


# ============================================================
# GEOGRAPHIC COHORTS
# ============================================================

def geographic_cohorts(
    entry: RankingEntry,
    all_entries: list[RankingEntry],
    subj: str,
    obj: str,
) -> list[Cohort]:

    cohorts: list[Cohort] = []

    city = _get(entry, "birth_city")
    state = _get(entry, "birth_state")
    country = _get(entry, "birth_country")

    # ---- city + state ----
    if city and state:
        def pred_city_state(e: RankingEntry):
            return e.birth_city == city and e.birth_state == state

        cohorts.append((
            "birth_city_state",
            pred_city_state,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among people from {city}, {state}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For those born in {city}, {state}, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {city}, {state} cohort, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- state / province ----
    if state:
        def pred_state(e: RankingEntry):
            return e.birth_state == state

        cohorts.append((
            "birth_state",
            pred_state,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among everyone born in {state}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For {state} natives, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {state} group, {{name}} sits at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- country (only when no state) ----
    if country and not state:
        def pred_country(e: RankingEntry):
            return e.birth_country == country

        cohorts.append((
            "birth_country",
            pred_country,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among everyone born in {country}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For people born in {country}, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {country}-born cohort, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    return cohorts


# ============================================================
# GROUP / VISIBILITY COHORTS
# ============================================================

def group_cohorts(
    entry: RankingEntry,
    all_entries: list[RankingEntry],
    subj: str,
    obj: str,
) -> list[Cohort]:

    cohorts: list[Cohort] = []

    # ---- adult performers (groups 5 + 6 only) ----
    if entry.group in (5, 6):
        def pred_adult(e: RankingEntry):
            return e.group in (5, 6)

        cohorts.append((
            "adult_performers",
            pred_adult,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        "Within the adult performers category, {name} ranks #{pos} of {total}",
                        "Among all adult performers listed, {name} comes in at #{pos} out of {total}",
                        "Looking only at adult performers, {name} places #{pos} of {total}",
                    ],
                )
            ],
        ))

    # ---- social media presence ----
    def has_social(e: RankingEntry):
        return bool(
            _get(e, "instagram") or
            _get(e, "twitter") or
            _get(e, "tiktok")
        )

    if has_social(entry):
        cohorts.append((
            "social_media",
            has_social,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        "Among people active on social media, {name} ranks #{pos} of {total}",
                        "Within the socially active group, {name} places #{pos} out of {total}",
                        "Looking at those with social profiles, {name} comes in at #{pos} of {total}",
                    ],
                )
            ],
        ))

    # ---- topless shown ----
    if "topless" in (_get(entry, "shown") or "").lower():
        def pred_topless(e: RankingEntry):
            return "topless" in (_get(e, "shown") or "").lower()

        cohorts.append((
            "shown_topless",
            pred_topless,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        "Among those who have gone topless, {name} ranks #{pos} of {total}",
                        "Within the group with topless appearances on their resume, {name} places #{pos} out of {total}",
                        "Looking only at topless appearances, {name} comes in at #{pos} of {total}",
                    ],
                )
            ],
        ))

    return cohorts


# ============================================================
# ATTRIBUTE COHORT HELPERS
# ============================================================

def _numeric(value: Optional[str]) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _height_inches(height: Optional[str]) -> Optional[int]:
    if not height:
        return None
    import re
    m = re.search(r"(\d)'\s*(\d{1,2})", height)
    if not m:
        return None
    return int(m.group(1)) * 12 + int(m.group(2))


def _weight_lbs(weight: Optional[str]) -> Optional[int]:
    if not weight:
        return None
    import re
    m = re.search(r"(\d{2,3})", weight)
    return int(m.group(1)) if m else None


def _measurement_tuple(entry: RankingEntry):
    b = _numeric(_get(entry, "bust"))
    w = _numeric(_get(entry, "waist"))
    h = _numeric(_get(entry, "hips"))
    if b and w and h:
        return (b, w, h)
    return None


# ============================================================
# MEASUREMENT COHORTS
# ============================================================

def measurement_cohorts(entry, all_entries, subj, obj) -> list[Cohort]:
    cohorts: list[Cohort] = []

    # ---- height over / under 5'5" ----
    inches = _height_inches(_get(entry, "height"))
    if inches:
        pivot = 65
        label = "over 5'5\"" if inches > pivot else "5'5\" or shorter"

        def pred_height(e):
            hi = _height_inches(_get(e, "height"))
            return hi and (hi > pivot if inches > pivot else hi <= pivot)

        cohorts.append((
            "height_split",
            pred_height,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those {label}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For people {label}, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {label} height group, {{name}} places #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- weight over / under 140 ----
    weight = _weight_lbs(_get(entry, "weight"))
    if weight:
        pivot = 140
        label = "over 140 lbs" if weight > pivot else "140 lbs or under"

        def pred_weight(e):
            w = _weight_lbs(_get(e, "weight"))
            return w and (w > pivot if weight > pivot else w <= pivot)

        cohorts.append((
            "weight_split",
            pred_weight,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those weighing {label}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For people {label}, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {label} weight group, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- bra size ----
    bra = _get(entry, "bra_size")
    if bra:
        def pred_bra(e):
            return _get(e, "bra_size") == bra

        cohorts.append((
            "bra_size",
            pred_bra,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those wearing a {bra} bra, {{name}} ranks #{{pos}} of {{total}}",
                        f"For the {bra} bra size group, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {bra} bra cohort, {{name}} places #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- cup size ----
    cup = _get(entry, "cup_size")
    if cup:
        def pred_cup(e):
            return _get(e, "cup_size") == cup

        cohorts.append((
            "cup_size",
            pred_cup,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those with {cup} cup size, {{name}} ranks #{{pos}} of {{total}}",
                        f"For the {cup}-cup group, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {cup} cup cohort, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- measurements ratio ----
    meas = _measurement_tuple(entry)
    if meas:
        b, w, h = meas
        ratio = round(b / w, 2)

        def pred_ratio(e):
            m = _measurement_tuple(e)
            return m and round(m[0] / m[1], 2) == ratio

        cohorts.append((
            "bust_waist_ratio",
            pred_ratio,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those with a {ratio} bust-to-waist ratio, {{name}} ranks #{{pos}} of {{total}}",
                        f"For the {ratio} ratio group, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {ratio} ratio cohort, {{name}} places #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    return cohorts


# ============================================================
# BODY / APPEARANCE COHORTS
# ============================================================

def appearance_cohorts(entry, all_entries, subj, obj) -> list[Cohort]:
    cohorts: list[Cohort] = []

    for field, label in [
        ("hair_color", "hair"),
        ("eye_color", "eyes"),
        ("body_type", "body type"),
        ("ethnicity", "ethnicity"),
        ("nationality", "nationality"),
    ]:
        val = _get(entry, field)
        if not val:
            continue

        def make_pred(v):
            return lambda e: _get(e, field) == v

        cohorts.append((
            field,
            make_pred(val),
            [
                lambda p, t, v=val, l=label: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those with {v} {l}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For people with {v} {l}, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {v} {l} group, {{name}} places #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    # ---- boobs: natural vs enhanced ----
    boobs = (_get(entry, "boobs") or "").lower()
    if boobs in ("natural", "enhanced"):
        def pred_boobs(e):
            return (_get(e, "boobs") or "").lower() == boobs

        cohorts.append((
            "boobs_type",
            pred_boobs,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those with {boobs} breasts, {{name}} ranks #{{pos}} of {{total}}",
                        f"For the {boobs}-boobs group, {{name}} comes in at #{{pos}} out of {{total}}",
                        f"Within the {boobs} category, {{name}} places #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    return cohorts


# ============================================================
# CAREER COHORTS
# ============================================================

def career_cohorts(entry, all_entries, subj, obj) -> list[Cohort]:
    cohorts: list[Cohort] = []

    # ---- occupations ----
    occ = _get(entry, "occupations")
    if occ:
        roles = [o.strip() for o in occ.split(",") if o.strip()]
        for role in roles:
            def pred_role(e, r=role):
                return r in (_get(e, "occupations") or "")

            cohorts.append((
                f"occupation_{role}",
                pred_role,
                [
                    lambda p, t, r=role: _rank_sentence(
                        p, t, entry, subj, obj,
                        [
                            f"Among those who work as {r}s, {{name}} ranks #{{pos}} of {{total}}",
                            f"For people in {r} roles, {{name}} comes in at #{{pos}} out of {{total}}",
                            f"Within the {r} profession, {{name}} places #{{pos}} of {{total}}",
                        ],
                    )
                ],
            ))

    # ---- years active ----
    years = _get(entry, "years_active")
    if years:
        def pred_years(e):
            return _get(e, "years_active") == years

        cohorts.append((
            "years_active",
            pred_years,
            [
                lambda p, t: _rank_sentence(
                    p, t, entry, subj, obj,
                    [
                        f"Among those active for {years}, {{name}} ranks #{{pos}} of {{total}}",
                        f"For careers spanning {years}, {{name}} places #{{pos}} out of {{total}}",
                        f"Within the {years}-active group, {{name}} comes in at #{{pos}} of {{total}}",
                    ],
                )
            ],
        ))

    return cohorts


# ============================================================
# FINAL FACT GENERATOR
# ============================================================

def generate_fun_facts(
    entry: RankingEntry,
    all_entries: Iterable[RankingEntry],
    *,
    today: Optional[datetime.date] = None,
    max_facts: int = 2,
    used_categories: Optional[set[str]] = None,
    exclude_categories: Optional[set[str]] = None,
) -> list[str]:

    if used_categories is None:
        used_categories = set()
    if exclude_categories is None:
        exclude_categories = set()

    entries = list(all_entries)
    subj, obj, _ = _pronouns(entry)

    cohorts: list[Cohort] = []
    cohorts += temporal_cohorts(entry, entries, today, subj, obj)
    cohorts += geographic_cohorts(entry, entries, subj, obj)
    cohorts += group_cohorts(entry, entries, subj, obj)
    cohorts += measurement_cohorts(entry, entries, subj, obj)
    cohorts += appearance_cohorts(entry, entries, subj, obj)
    cohorts += career_cohorts(entry, entries, subj, obj)

    random.shuffle(cohorts)

    facts: list[str] = []

    for cid, pred, formatters in cohorts:
        if len(facts) >= max_facts:
            break
        if cid in used_categories or cid in exclude_categories:
            continue

        cohort = [e for e in entries if pred(e)]
        if len(cohort) < 2:
            continue

        ranked = sorted(
            cohort,
            key=lambda e: (
                e.numeric_rank if e.numeric_rank is not None else 10_000,
                e.name,
            ),
        )

        if entry not in ranked:
            continue

        pos = ranked.index(entry) + 1
        total = len(ranked)

        sentence = random.choice(formatters)(pos, total)
        facts.append(f"• {sentence}")
        used_categories.add(cid)

    return facts

