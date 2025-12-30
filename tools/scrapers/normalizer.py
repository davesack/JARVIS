from typing import Any, Dict


class Normalizer:
    """
    Normalization helpers: measurement cleanup, case fixing, and consistency rules.
    """

    @staticmethod
    def clean_measurement(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        try:
            v = float(str(value).replace(",", "").strip())
            return v
        except Exception:
            return None

    @staticmethod
    def clean_string(value: Any) -> str:
        if not value:
            return ""
        return str(value).strip()

    @staticmethod
    def clean_list(value: Any) -> list:
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [str(value)]

    @staticmethod
    def normalize_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply core normalization rules to the merged metadata object.
        """
        if not data:
            return data

        out = {}

        for k, v in data.items():
            if isinstance(v, str):
                out[k] = v.strip()
            else:
                out[k] = v

        return out
