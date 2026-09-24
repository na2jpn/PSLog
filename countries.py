"""CTY.DAT country hints; not historical DXCC credit or WPX computation."""
import re,sys,hashlib,json
from pathlib import Path
from storage import StorageError

class Countries:
    def __init__(self,text):
        self.prefixes={};self.exact={}
        for block in text.split(';'):
            if not block.strip():continue
            parts=block.strip().split(':',8)
            if len(parts)!=9:raise ValueError('CTY header')
            name,cq,itu,continent,lat,lon,offset,primary,aliases=[x.strip() for x in parts]
            if continent not in ('AF','AN','AS','EU','NA','OC','SA'):raise ValueError('continent')
            int(cq);int(itu);float(lat);float(lon);float(offset)
            if primary.startswith('*'):continue # WAE-only entities are not used for country hints.
            for alias in aliases.replace('\n','').replace('\r','').split(','):
                alias=alias.strip()
                if not alias:continue
                m=re.fullmatch(r'(=?[A-Z0-9/]+)((?:\([^)]*\)|\[[^]]*\]|<[^>]*>|\{[^}]*\}|~[^~]*~)*)',alias)
                if not m:raise ValueError('CTY alias: '+alias)
                token,extra=m.groups();override=re.search(r'\{([A-Z]{2})\}',extra)
                itu_override=re.search(r'\[([0-9]+)\]',extra)
                row={'country':name,'continent':override[1] if override else continent,
                     'entity_prefix':primary,'cq':int(cq),'itu':int(itu_override[1]) if itu_override else int(itu),
                     'matched':token}
                table=self.exact if token.startswith('=') else self.prefixes
                table.setdefault(token.lstrip('='),row)
        if not self.prefixes:raise ValueError('empty CTY')
    def lookup(self,call):
        call=call.strip().upper()
        if not re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*',call):return None
        # Explicit uncertain operation locations must not fall back to home country.
        if not re.search('[A-Z]',call) or not re.search('[0-9]',call):return None
        if call.endswith(('/MM','/AM')):return None
        if call in self.exact:return dict(self.exact[call])
        if call.startswith('JD1') or '/JD1' in call:return None
        if '/' in call:
            base,suffix=call.rsplit('/',1)
            if '/' in base:return None
            if suffix not in ('P','QRP') and not (suffix.isdigit() and re.match(r'(J[A-S]|[78][J-N])\d',base)):return None
            call=base
        found=next((self.prefixes[call[:n]] for n in range(len(call),0,-1) if call[:n] in self.prefixes),None)
        return dict(found) if found else None

def load(root):
    path=Path(root)/'config/db/cty.dat'
    if not path.exists():path=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'config/db/cty.dat'
    try:
        raw=path.read_bytes();meta=json.loads(path.with_name('cty_meta.json').read_text('utf-8'))
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('DBと更新情報が一致しません。')
        data=Countries(raw.decode('ascii'));data.version=meta['version'];return data
    except (OSError,ValueError,UnicodeError,KeyError,TypeError) as e:raise StorageError('国名参照DBを読み込めません: '+str(e)) from e
