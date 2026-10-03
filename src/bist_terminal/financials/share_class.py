from __future__ import annotations
from pathlib import Path
import re
import unicodedata


def normalize_company_title(value):
    text=str(value or "").upper().replace("İ","I")
    text=unicodedata.normalize("NFKD",text)
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    text=re.sub(r"[^A-Z0-9]+"," ",text)
    return re.sub(r"\s+"," ",text).strip()


def source_filename_names_ticker(source_file, ticker):
    base=Path(str(source_file or "")).name.upper()
    return bool(re.search(rf"(^|[-_]){re.escape(str(ticker).upper())}([-_]|$)",base))
