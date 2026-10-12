"""Compare published workbook scalar fields against the canonical dashboard.

Nested lineage structures are string-rendered by pandas; the JSON remains their
canonical representation. All scalar fields, including N/A and dates, are checked.
"""
from pathlib import Path
import json
import math

import openpyxl


def validate(payload, workbook_path):
    book = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        rows = book['All Stocks'].iter_rows(values_only=True)
        header = next(rows)
        assert len(header) == len(set(header)), 'duplicate Excel columns'
        sheet = {}
        for values in rows:
            row = dict(zip(header, values))
            ticker = row['ticker']
            assert ticker not in sheet, 'duplicate Excel ticker'
            sheet[ticker] = row
        stocks = payload['stocks']
        assert set(sheet) == {r['ticker'] for r in stocks}, 'Excel/JSON universe mismatch'
        checked = 0
        for stock in stocks:
            for key, value in stock.items():
                if isinstance(value, (dict, list)):
                    continue
                assert key in header, f'missing Excel column {key}'
                actual = sheet[stock['ticker']][key]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    same = isinstance(actual, (int, float)) and math.isclose(actual, value, rel_tol=1e-12, abs_tol=1e-12)
                else:
                    same = actual == value or (value == '' and actual is None)
                assert same, f"Excel/JSON mismatch: {stock['ticker']}.{key}"
                checked += 1
        return checked
    finally:
        book.close()


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'dashboard/data/latest.json').read_text())
    print('EXCEL_CANONICAL_PASS', validate(data, root / 'artifacts/BIST_Research_Latest.xlsx'), 'scalar fields')
