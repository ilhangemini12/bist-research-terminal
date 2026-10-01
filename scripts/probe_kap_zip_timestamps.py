"""Probe whether KAP bulk ZIP entry timestamps preserve notification time."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from bist_terminal.financials.kap_bulk import KapBulkFinancialProvider

TARGETS={
    'THYAO_1565996_2025_4.xls',
    'ASELS_1561039_2025_4.xls',
    'AKBNK_1551575_2025_4.xls',
}

def main():
    arc=KapBulkFinancialProvider().download_archive(2025,'4')
    for info in arc.zip.infolist():
        base=info.filename.rsplit('/',1)[-1]
        if base in TARGETS:
            print(
                f'KAP_ZIP_TIMESTAMP file={base} date_time={info.date_time} '
                f'create_system={info.create_system} external_attr={info.external_attr}'
            )

if __name__=='__main__':
    main()
