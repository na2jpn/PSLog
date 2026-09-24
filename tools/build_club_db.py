"""Convert a downloaded official list; never execute its scripts or collect contacts."""
from html.parser import HTMLParser
from pathlib import Path
import sys,csv,io,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clubs import number,INDEX_URL,LIST_URL

class Parser(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None;self.active=False
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.active=False
        if tag=='tr':self.row=[]
        elif tag=='td' and self.row is not None:self.cell=[]
        elif tag=='br' and self.cell is not None:self.cell.append(' ')
    def handle_data(self,text):
        if self.cell is not None:self.cell.append(text)
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:self.row.append(''.join(self.cell).strip());self.cell=None
        if tag=='tr' and self.row is not None:
            if self.row and self.row[0]=='登録番号':self.active=True
            elif self.row and self.active:
                if len(self.row)!=4:raise ValueError('公式リストの列構成が変わっています。')
                self.rows.append({'number':number(self.row[0]),'name':self.row[1]})
            self.row=None

def build(source,output,checked,valid_from,valid_to):
    raw=Path(source).read_bytes();p=Parser();p.feed(raw.decode('cp932'));rows=p.rows
    if len({r['number'] for r in rows})!=len(rows) or not rows:raise ValueError('登録番号が重複、または空のリストです。')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=['number','name'],lineterminator='\r\n');writer.writeheader();writer.writerows(rows);data=out.getvalue().encode('utf-8-sig');folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    meta=dict(schema=1,count=len(rows),source_url=LIST_URL,index_url=INDEX_URL,checked_at=checked,valid_from=valid_from,valid_to=valid_to,sha256=hashlib.sha256(data).hexdigest(),source_sha256=hashlib.sha256(raw).hexdigest())
    (folder/'club_db.csv').write_bytes(data);(folder/'club_db_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(f'{len(rows)} clubs')
if __name__=='__main__':build(*sys.argv[1:])
