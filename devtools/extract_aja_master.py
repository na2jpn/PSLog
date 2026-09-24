"""Extract the historical city/gun/ward row order from the supplied JARL AJA sheet."""
from pathlib import Path
import hashlib,json,re,sys
import xlrd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/activity-research/sources/AJA-list_202401.xls'
TARGET=ROOT/'config/db/aja_locations.json'

def text(cell):
    value=cell.value
    if isinstance(value,float) and value.is_integer():value=str(int(value))
    value=str(value).replace('\t',' ').replace('\u3000',' ')
    return re.sub(r'\s+',' ',value).strip()

def main():
    sheet=xlrd.open_workbook(str(SOURCE),formatting_info=False).sheet_by_name('AJA-List')
    rows=[];prefecture=''
    for index in range(3,sheet.nrows):
        code=text(sheet.cell(index,3))
        if not re.fullmatch(r'\d{4,6}',code):continue
        if text(sheet.cell(index,1)):prefecture=text(sheet.cell(index,1))
        name=text(sheet.cell(index,2)) or text(sheet.cell(index,1))
        name=re.sub(r'\s*[（(]\d{4}\.\d{1,2}\.\d{1,2}[)）]\s*','',name).strip()
        rows.append({'code':code,'name':name,'prefecture':prefecture,'kind':{4:'city',5:'gun',6:'ward'}[len(code)],'legacy_row':index+1})
    if len(rows)!=1713:raise ValueError(f'expected 1713 AJA locations, got {len(rows)}')
    data={'schema':1,'source':'AJA-list_202401.xls','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rows':rows}
    TARGET.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(TARGET,len(rows))

if __name__=='__main__':main()
