from __future__ import annotations
from pathlib import Path
import pandas as pd

SHEETS=['Dashboard','All Stocks','BIST30','BIST100','Banks','Insurance','Brokerage','Industrials','RSI Scanner','Value Scanner','Quality Scanner','Growth Scanner','Ozkan Filiz','Volkan Kocabas','Technical','Fundamentals','Growth','Target Prices','Model Portfolios','KAP News','Data Quality','Source Status','Sources']

def export_excel(tables:dict[str,pd.DataFrame],path='artifacts/BIST_Research_Latest.xlsx'):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with pd.ExcelWriter(path,engine='xlsxwriter') as writer:
        book=writer.book
        hdr=book.add_format({'bold':True,'font_color':'white','bg_color':'#0f172a','border':0})
        neg=book.add_format({'font_color':'red','num_format':'#,##0.00;[Red](#,##0.00);-'})
        for name in SHEETS:
            df=tables.get(name,pd.DataFrame())
            if df.empty: df=pd.DataFrame({'Status':['No data / N/A']})
            df.to_excel(writer,sheet_name=name,index=False)
            ws=writer.sheets[name]; ws.freeze_panes(1,0); ws.hide_gridlines(2); ws.autofilter(0,0,max(len(df),1),max(len(df.columns)-1,0))
            for c,col in enumerate(df.columns):
                ws.write(0,c,col,hdr); width=min(max(len(str(col))+2,12),28); ws.set_column(c,c,width)
    return path
