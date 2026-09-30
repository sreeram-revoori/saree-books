"""Where the books are kept: a Google Sheet (when configured) or a local Excel file.

Google Sheets is used when `.streamlit/secrets.toml` (or the Streamlit Cloud
secrets box) has a [gcp_service_account] section and a `spreadsheet` link.
Otherwise the app keeps `saree_books.xlsx` next to this file.
"""
from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import books

BASE_DIR = Path(__file__).parent


class ExcelStore:
    """saree_books.xlsx on this computer, with a timestamped backup before every save."""

    label = "Excel file on this computer"
    WORKBOOK = BASE_DIR / "saree_books.xlsx"
    BACKUP_DIR = BASE_DIR / "backups"
    MAX_BACKUPS = 60

    def read(self) -> dict[str, pd.DataFrame]:
        if not self.WORKBOOK.exists():
            return {}
        return pd.read_excel(self.WORKBOOK, sheet_name=None)

    def write(self, sheets: dict[str, pd.DataFrame]) -> None:
        self._backup()
        tmp = self.WORKBOOK.with_suffix(".tmp.xlsx")
        books.write_xlsx(sheets, tmp)
        tmp.replace(self.WORKBOOK)

    def _backup(self) -> None:
        if not self.WORKBOOK.exists():
            return
        self.BACKUP_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy2(self.WORKBOOK, self.BACKUP_DIR / f"saree_books_{stamp}.xlsx")
        for old in sorted(self.BACKUP_DIR.glob("saree_books_*.xlsx"))[:-self.MAX_BACKUPS]:
            old.unlink()


def _cell(v):
    """Turn a pandas value into something the Google Sheets API accepts."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    if hasattr(v, "item"):  # numpy number
        v = v.item()
    if isinstance(v, float):
        return int(v) if v.is_integer() else round(v, 2)
    return v


class SheetsStore:
    """A Google Sheet shared with a Google service account."""

    label = "Google Sheet"
    HEADER_BG = {"red": 0.48, "green": 0.12, "blue": 0.23}  # deep maroon

    def __init__(self, credentials: dict, spreadsheet: str):
        import gspread

        client = gspread.service_account_from_dict(credentials)
        self.book = (client.open_by_url(spreadsheet) if spreadsheet.startswith("http")
                     else client.open_by_key(spreadsheet))
        self.url = self.book.url
        self._formatted: dict[str, list[str]] = {}

    def read(self) -> dict[str, pd.DataFrame]:
        titles = {ws.title for ws in self.book.worksheets()}
        names = [n for n in books.INPUT_SHEETS if n in titles]
        if not names:
            return {}
        res = self.book.values_batch_get(
            [f"'{n}'" for n in names], params={"valueRenderOption": "UNFORMATTED_VALUE"}
        )
        out = {}
        for name, block in zip(names, res.get("valueRanges", [])):
            rows = block.get("values", [])
            if not rows:
                continue
            header, body = rows[0], rows[1:]
            body = [r + [""] * (len(header) - len(r)) for r in body]
            out[name] = pd.DataFrame([r[:len(header)] for r in body], columns=header)
        return out

    def write(self, sheets: dict[str, pd.DataFrame]) -> None:
        existing = {ws.title: ws for ws in self.book.worksheets()}
        for name, df in sheets.items():
            if name not in existing:
                spare = existing.get("Sheet1")
                if spare is not None and not spare.get_all_values():
                    spare.update_title(name)
                    existing[name] = existing.pop("Sheet1")
                else:
                    existing[name] = self.book.add_worksheet(name, rows=1000, cols=len(df.columns))
        data, clear = [], []
        for name, df in sheets.items():
            ws = existing[name]
            rows = [list(df.columns)] + [[_cell(v) for v in r] for r in df.itertuples(index=False)]
            if len(rows) > ws.row_count or len(df.columns) > ws.col_count:
                ws.resize(rows=max(ws.row_count, len(rows) + 500), cols=max(ws.col_count, len(df.columns)))
            data.append({"range": f"'{name}'!A1", "values": rows})
            clear.append(f"'{name}'!A{len(rows) + 1}:ZZ")
        # One request writes every sheet, a second removes rows left over from before.
        self.book.values_batch_update({"valueInputOption": "RAW", "data": data})
        self.book.values_batch_clear(body={"ranges": clear})
        for name, df in sheets.items():
            if self._formatted.get(name) != list(df.columns):
                self._format(existing[name], list(df.columns))
                self._formatted[name] = list(df.columns)

    def _format(self, ws, cols: list[str]) -> None:
        from gspread.utils import rowcol_to_a1

        formats = [{
            "range": f"A1:{rowcol_to_a1(1, len(cols))}",
            "format": {"backgroundColor": self.HEADER_BG, "wrapStrategy": "WRAP",
                       "horizontalAlignment": "CENTER",
                       "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}},
        }]
        for i, col in enumerate(cols, start=1):
            letter = rowcol_to_a1(1, i)[:-1]
            if col in books.QTY_COLS:
                pattern = "0"
            elif books.is_number_col(col):
                pattern = "#,##0.00"
            else:
                continue
            formats.append({"range": f"{letter}2:{letter}",
                            "format": {"numberFormat": {"type": "NUMBER", "pattern": pattern}}})
        ws.batch_format(formats)
        ws.freeze(rows=1)


def secrets() -> dict:
    import streamlit as st

    try:
        return {k: st.secrets[k] for k in st.secrets}
    except Exception:  # no secrets file at all
        return {}


def open_store():
    s = secrets()
    if "gcp_service_account" in s and s.get("spreadsheet"):
        return SheetsStore(dict(s["gcp_service_account"]), s["spreadsheet"])
    return ExcelStore()
