import config
from datetime import datetime


class RowMapper:
    def build_row(self, record: dict) -> list:
        cols = config.GOOGLE_SHEETS["rankings"]["columns"]

        row = [""] * 60  # safely oversized

        def set_col(key, value):
            col_letter = cols.get(key)
            if not col_letter:
                return
            idx = ord(col_letter) - ord("A")
            row[idx] = value

        meta = record.get("metadata", {})

        set_col("name", record["name"])
        set_col("slug", meta.get("slug"))
        set_col("known_for", meta.get("known_for"))
        set_col("birthdate", meta.get("birthdate"))
        set_col("place_of_birth", meta.get("place_of_birth"))

        # Physical
        set_col("height", meta.get("height"))
        set_col("waist", meta.get("waist"))
        set_col("hips", meta.get("hips"))
        set_col("glutes", meta.get("glutes"))
        set_col("eyes", meta.get("eyes"))
        set_col("hair", meta.get("hair"))

        # Social
        set_col("instagram", meta.get("instagram"))
        set_col("twitter", meta.get("twitter"))

        # Tracking
        set_col("distinguishing_features", "AUTO_ADDED")
        set_col("rank", "")
        set_col("group", "")

        return row
