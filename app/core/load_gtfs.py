import zipfile
import io
import re
import unicodedata
import pandas as pd
from typing import Dict
from pandas.api import types as pdtypes


def _clean_text(value: str) -> str:
    """Normalize and clean a single text value.

    - Normalize unicode (NFKC)
    - Remove BOM and zero-width / weird spaces
    - Remove C0/C1 control characters
    - Collapse multiple whitespace into single space and strip
    """
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return value

    # Normalize unicode form
    value = unicodedata.normalize("NFKC", value)

    # Remove BOM and invisible characters
    value = value.replace("\ufeff", "")
    value = value.replace("\u200b", "")
    value = value.replace("\u00a0", " ")

    # Remove ASCII control characters (except tab/newline if present)
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", value)

    # Replace any sequence of whitespace (tabs/newlines/spaces) with a single space
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _clean_column_name(name: str) -> str:
    try:
        name = str(name)
    except Exception:
        return name
    name = unicodedata.normalize("NFKC", name)
    name = name.replace("\ufeff", "")
    return name.strip()


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean all text columns and column names of a dataframe in-place (returns df).

    Only object/string dtype columns are touched to avoid changing numeric types.
    """
    # Clean column names
    df.columns = [_clean_column_name(c) for c in df.columns]

    for col in df.columns:
        try:
            if pdtypes.is_object_dtype(df[col]) or pdtypes.is_string_dtype(df[col]):
                # apply cleaning but keep NaN as-is
                df[col] = df[col].apply(lambda v: _clean_text(v) if pd.notna(v) else v)
        except Exception:
            # If any unexpected error happens, skip cleaning that column
            continue
    return df


def load_gtfs_from_zip(zip_path: str) -> Dict[str, pd.DataFrame]:
    """Carga archivos GTFS comunes desde un ZIP y devuelve dataframes.

    Soporta: stops.txt, routes.txt, trips.txt, stop_times.txt, calendar.txt, agency.txt
    Se limpian los textos de cada fichero para eliminar espacios raros y caracteres de control.
    """
    dfs = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt", "agency.txt"]:
            if name in z.namelist():
                with z.open(name) as f:
                    try:
                        # pandas can read from file-like objects
                        df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8"), low_memory=False)
                    except Exception:
                        # retry with latin-1 encoding for some GTFS files
                        f.seek(0)
                        df = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), low_memory=False)

                # Clean dataframe text fields
                try:
                    df = _clean_dataframe(df)
                except Exception:
                    # best-effort: if cleaning fails, keep original df
                    pass

                dfs[name.replace(".txt", "")] = df
    return dfs
