"""QSL receipt matching and guarded TXT updates with mandatory result files."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from bisect import bisect_left
import csv, io, json, re, unicodedata, uuid, hashlib
from model import QSL_FLAGS, validate_station
from search import search, Criteria, file_identity
from storage import Snapshot, StorageError, ExternalChange, operation_lock, replace_bytes, parse, VERSION

from qsl_marks import METHODS, tokens, change, buro_judgement, receipt_state

@dataclass
class Entry:
    number: int
    raw: str
    stamp: object = None
    call: str = ''
    code: str = ''
    reason: str = ''
    candidates: list = field(default_factory=list)
    nearby: list = field(default_factory=list)
    around: list = field(default_factory=list)
    manual_candidates: list = field(default_factory=list)
    selected: list = field(default_factory=list)
    pick: object = None

@dataclass
class Plan:
    source: Path
    snapshot: Snapshot
    own: str
    zone: str
    method: str
    encoding: str
    entries: list
    snapshots: dict
    consumed: bool = False

def read_entries(data,zone,encoding):
    if zone not in ('JST','UTC'):raise StorageError('JSTまたはUTCを選択してください。')
    if encoding not in ('utf-8-sig','cp932'):raise StorageError('文字コードを選択してください。')
    try:text=data.decode(encoding)
    except UnicodeDecodeError as e:raise StorageError('指定文字コードで読み込めません。') from e
    entries=[]
    for number,raw in enumerate(text.splitlines(),1):
        row=Entry(number,raw);entries.append(row)
        parts=unicodedata.normalize('NFKC',raw).strip().upper().split()
        if not parts:row.reason='空行';continue
        dates=[(i,x) for i,x in enumerate(parts) if re.fullmatch(r'[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}',x)]
        times=[(i,x) for i,x in enumerate(parts) if re.fullmatch(r'[0-9]{1,2}:[0-9]{2}',x)]
        codes=[(i,x) for i,x in enumerate(parts) if re.fullmatch(r'(?:[0-9]{4}|[0-9]{6}|[0-9]{5}[A-Z]?)',x)]
        code_indexes={i for i,_ in codes}
        calls=[(i,x) for i,x in enumerate(parts) if i not in code_indexes and re.fullmatch(r'[A-Z0-9]+(?:/[A-Z0-9]+)*',x) and re.search('[A-Z]',x) and re.search('[0-9]',x)]
        optional_code=(len(parts)==3 and len(codes)==0) or (len(parts)==4 and len(codes)==1)
        if len(parts) not in (3,4) or len(dates)!=1 or len(times)!=1 or len(calls)!=1 or not optional_code:
            row.reason='書式不正：日付・時刻・コールの3項目、またはJCC/JCGを加えた4項目が必要';continue
        try:
            row.stamp=datetime.strptime(dates[0][1].replace('/','-')+' '+times[0][1],'%Y-%m-%d %H:%M')
            if zone=='UTC':row.stamp+=timedelta(hours=9)
            row.call=calls[0][1]
            row.code=codes[0][1] if codes else ''
        except (ValueError,OverflowError):row.stamp=None;row.reason='書式不正：日付または時刻の値'
    return entries

def scope_files(repo,own):
    result=[]
    for path in repo.book.glob('*.txt'):
        identity=file_identity(path)
        if identity and (identity[1]==own or identity[1].startswith(own+'/')):result.append(path.resolve())
    return sorted(result)

def _base_call(value):
    return str(value or '').upper().split('/',1)[0]

def _nearest(values,stamp,limit=3):
    ranked=sorted(values,key=lambda x:(abs((x[0]-stamp).total_seconds()),x[0],str(x[1].path),x[1].line))
    return [h for _,h in ranked[:limit]]

def _window(values, stamps, stamp, seconds=180):
    """Return every QSO inside a clock window, regardless of callsign."""
    left=bisect_left(stamps,stamp-timedelta(seconds=seconds))
    right=bisect_left(stamps,stamp+timedelta(seconds=seconds)+timedelta(microseconds=1))
    return [h for _,h in values[left:right]]

def _call_parts(value):
    value=str(value or '').strip().upper()
    base,*portable=value.split('/',1)
    suffix='/'+portable[0] if portable else ''
    match=re.fullmatch(r'([A-Z0-9]+)([0-9])([A-Z]+)',base)
    if match:return (match.group(1),match.group(2),match.group(3),suffix)
    return (base,'','',suffix)

def call_difference(expected, actual):
    """Human-readable callsign difference for typo investigation."""
    expected=str(expected or '').strip().upper();actual=str(actual or '').strip().upper()
    if expected==actual:return '同一コール'
    ep,ea,es,em=_call_parts(expected);ap,aa,ass,am=_call_parts(actual);parts=[]
    if ep!=ap:parts.append(f'プリフィックス差 {ep or "(空欄)"} ↔ {ap or "(空欄)"}')
    if ea!=aa:parts.append(f'エリア数字差 {ea or "(なし)"} ↔ {aa or "(なし)"}')
    if es!=ass:parts.append(f'サフィックス差 {es or "(なし)"} ↔ {ass or "(なし)"}')
    if em!=am:parts.append(f'移動表記差 {em or "(なし)"} ↔ {am or "(なし)"}')
    if parts:return ' / '.join(parts)
    # Non-standard/special calls: still expose exact character differences.
    diffs=[]
    for i in range(max(len(expected),len(actual))):
        a=expected[i] if i<len(expected) else '∅';b=actual[i] if i<len(actual) else '∅'
        if a!=b:diffs.append(f'{i+1}文字目 {a}↔{b}')
    return '文字差 '+', '.join(diffs[:6]) if diffs else '表記差あり'

def _hit_key(hit):
    return (str(Path(hit.path).resolve()),int(hit.line))

def selected_hits(entry):
    """Return selected QSO hits in stable display order.

    ``pick`` is kept for backward compatibility with the older one-choice
    implementation, while ``selected`` supports the real hQSL case where one
    received card can confirm multiple logged QSOs.
    """
    keys={_hit_key(h) for h in getattr(entry,'selected',[]) if h is not None}
    if not keys and isinstance(entry.pick,int) and 0<=entry.pick<len(entry.candidates):
        keys.add(_hit_key(entry.candidates[entry.pick]))
    ordered=[];seen=set()
    for hit in list(entry.candidates)+list(getattr(entry,'manual_candidates',[])):
        key=_hit_key(hit)
        if key in keys and key not in seen:
            ordered.append(hit);seen.add(key)
    return ordered

def set_selected(entry,hit,checked):
    """Select/deselect one candidate and keep legacy ``pick`` synchronized."""
    key=_hit_key(hit)
    current=[];seen=set()
    for existing in getattr(entry,'selected',[]):
        ekey=_hit_key(existing)
        if ekey!=key and ekey not in seen:
            current.append(existing);seen.add(ekey)
    if checked and key not in seen:
        current.append(hit)
    entry.selected=current
    chosen=selected_hits(entry)
    if len(chosen)==1:
        try:entry.pick=next(i for i,h in enumerate(entry.candidates) if _hit_key(h)==_hit_key(chosen[0]))
        except StopIteration:entry.pick=None
    else:entry.pick=None

def prepare(repo,source,own,zone,method,encoding='utf-8-sig'):
    own=validate_station(unicodedata.normalize('NFKC',own),'')
    if '/' in own:raise StorageError('対象には移動サフィックスを除いた基本コールを入力してください。')
    if method not in METHODS:raise StorageError('受領方法を選択してください。')
    source=Path(source).resolve();snapshot=Snapshot.read(source)
    if snapshot.data is None:raise StorageError('受領一覧TXTがありません。')
    entries=read_entries(snapshot.data,zone,encoding)
    paths=scope_files(repo,own);snapshots={p:Snapshot.read(p) for p in paths}
    results=search(repo,Criteria(own,portable=True))
    if results.problems:raise StorageError('対象ログに読み取り問題があります。先に修正してください。\n'+'\n'.join(results.problems))
    for hit in results.hits:
        if hit.snapshot!=snapshots.get(hit.path):raise ExternalChange('照合中にログが変更されました。再照合してください。')
    index={};base_index={}
    for hit in results.hits:
        stamp=datetime.strptime(hit.qso.date+' '+hit.qso.time,'%Y-%m-%d %H:%M')
        index.setdefault(hit.qso.call.upper(),[]).append((stamp,hit))
        base_index.setdefault(_base_call(hit.qso.call),[]).append((stamp,hit))
    for values in index.values():values.sort(key=lambda x:x[0])
    for values in base_index.values():values.sort(key=lambda x:x[0])
    stamps={call:[x[0] for x in values] for call,values in index.items()}
    all_values=sorted(((datetime.strptime(hit.qso.date+' '+hit.qso.time,'%Y-%m-%d %H:%M'),hit) for hit in results.hits),key=lambda x:x[0])
    all_stamps=[x[0] for x in all_values]
    for row in entries:
        if row.stamp is None:continue
        row.around=_window(all_values,all_stamps,row.stamp,180)
        values=index.get(row.call,[]);ts=stamps.get(row.call,[])
        # QSL mail clocks and manual logs can differ slightly.  Accept exactly
        # +/-5 minutes; 5:01 is already outside the automatic match window.
        pos=bisect_left(ts,row.stamp);left=pos;right=pos
        while left>0 and (row.stamp-ts[left-1]).total_seconds()<=300:left-=1
        while right<len(ts) and (ts[right]-row.stamp).total_seconds()<=300:right+=1
        row.candidates=[h for _,h in values[left:right]]
        if len(row.candidates)==1:
            row.pick=0
            row.selected=[row.candidates[0]]
            q=row.candidates[0].qso
            delta=int((datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M')-row.stamp).total_seconds()/60)
            row.reason='一致' if delta==0 else f'一致：時刻差 {delta:+d}分（許容±5分以内）'
            continue
        if len(row.candidates)>1:
            row.reason=f'複数候補：±5分以内に{len(row.candidates)}交信'
            row.nearby=list(row.candidates)
            continue
        row.manual_candidates=[h for h in row.around if call_difference(row.call,h.qso.call)!='同一コール']
        if values:
            row.nearby=_nearest(values,row.stamp)
            nearest=row.nearby[0];q=nearest.qso
            qstamp=datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M')
            if q.date==row.stamp.strftime('%Y-%m-%d'):
                delta=int((qstamp-row.stamp).total_seconds()/60)
                row.reason=f'未一致：時刻差 {delta:+d}分（許容±5分超過）'
            else:
                row.reason=f'未一致：コール一致・日付不一致（最も近いログ {q.date} {q.time}）'
            continue
        base_values=base_index.get(_base_call(row.call),[])
        if base_values:
            row.nearby=_nearest(base_values,row.stamp)
            q=row.nearby[0].qso
            row.reason=f'未一致：移動表記違いの可能性（近い候補 {q.call} {q.date} {q.time}）'
        else:
            row.reason='未一致：該当QSOなし（コール一致なし）'
    return Plan(source=source,snapshot=snapshot,own=own,zone=zone,method=method,encoding=encoding,entries=entries,snapshots=snapshots)

def _decision_for_hit(plan,entry,hit,seen):
    key=(hit.path,hit.line);current=receipt_state(hit.qso.remarks,plan.method)
    after,first,buro=change(hit.qso.remarks,plan.method)
    received=current['received'] and not current['sent'] and after==hit.qso.remarks
    manual=_hit_key(hit) in {_hit_key(x) for x in getattr(entry,'manual_candidates',[])}
    state='既受領スキップ' if received else '更新予定' if after!=hit.qso.remarks else '受領記録済み'
    reason=(f'既に {plan.method} 受領済み' if received else entry.reason)
    if manual and not received:
        diff=call_difference(entry.call,hit.qso.call)
        reason=f'{entry.reason} / 手動割当: {diff}'
    row={'entry':entry,'hit':hit,'state':state,'reason':reason,'first':first,'buro':buro,'buro_status':buro_judgement(hit.qso.remarks),'after':after,'duplicate_of':'','received':received,'manual':manual}
    if key in seen:row.update(state='同一交信の重複入力',reason=f'入力行{seen[key]}と同じQSOです',duplicate_of=seen[key])
    else:seen[key]=entry.number
    return row


def decisions(plan):
    rows=[];seen={}
    for entry in plan.entries:
        chosen=selected_hits(entry)
        if not chosen:
            if len(entry.candidates)>1:state='複数候補'
            elif entry.candidates:state='一致・未選択'
            elif getattr(entry,'manual_candidates',[]):state='手動候補'
            elif entry.stamp is None:state='書式不正'
            else:state='未一致'
            rows.append({'entry':entry,'hit':None,'state':state,'reason':entry.reason,'first':False,'buro':False,'buro_status':'','after':'','duplicate_of':'','received':False,'manual':False})
            continue
        for hit in chosen:
            rows.append(_decision_for_hit(plan,entry,hit,seen))
    return rows

def edited_bytes(session,changes):
    # Only the RMKS substring changes: preserve historical RST, whitespace and BOM.
    lines=[line.raw for line in session.log.lines]
    for number,remarks in changes.items():
        raw=lines[number-1];pipes=[m.start() for m in re.finditer(r'\|',raw)]
        start=pipes[8]+1;end=pipes[9] if len(pipes)>9 else raw.rfind('\\\\')
        field=raw[start:end];leading=field[:len(field)-len(field.lstrip())];trailing=field[len(field.rstrip()):]
        lines[number-1]=raw[:start]+leading+remarks+trailing+raw[end:]
    data=(b'\xef\xbb\xbf' if session.log.bom else b'')+''.join(lines).encode('utf-8')
    check=parse(data)
    if check.issues or any(check.lines[n-1].qso.remarks!=value for n,value in changes.items()):raise StorageError('更新用データの照合に失敗しました。')
    return data

COLUMNS=['処理ID','入力行','入力原文','入力時刻基準','入力日時JST','照合状態','候補一覧JSON','選択候補','時刻差秒_ログ引く一覧','初回QSL確認','BURO発送記録なし','確認理由','実自局コール','相手コール','DATE_JST','TIME_JST','日時UTC','BAND','MODE','RST送信','RST受信','HIS_QTH','MY_QTH','JCCJCG','RMKS更新前','RMKS更新予定','受領方法','原本パス','原本行','重複元入力行','更新状態','バックアップ','原本SHA256更新前','原本SHA256更新予定']

def candidate_data(hit):
    q=hit.qso
    return {'own':hit.own,'date':q.date,'time':q.time,'call':q.call,'band':q.band,'mode':q.mode,'his_qth':q.his_qth,'my_qth':q.my_qth,'jccjcg':q.code,'rmks':q.remarks,'path':str(hit.path),'line':hit.line}

def _selection_label(entry,hit):
    if not hit:return ''
    key=_hit_key(hit)
    for i,candidate in enumerate(entry.candidates,1):
        if _hit_key(candidate)==key:return str(i)
    for i,candidate in enumerate(getattr(entry,'manual_candidates',[]),1):
        if _hit_key(candidate)==key:return f'手動{i}'
    return ''

def utc_text(stamp):
    try:return (stamp-timedelta(hours=9)).strftime('%Y-%m-%d %H:%M')
    except OverflowError:return '変換範囲外'

def csv_bytes(plan,rows,state):
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=COLUMNS,lineterminator='\r\n');writer.writeheader()
    for row in rows:
        e=row['entry'];h=row['hit'];f=state['files'].get(str(h.path),{}) if h else {};q=h.qso if h else None
        stamp=datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M') if q else None
        status=f.get('status','未処理') if row['state']=='更新予定' else '更新対象外'
        if row['state']=='同一交信の重複入力':status='重複元に従う：'+f.get('status','変更なし')
        all_candidates=list(e.candidates)+list(getattr(e,'manual_candidates',[]))
        values=[state['id'],e.number,e.raw,plan.zone,e.stamp.isoformat(' ',timespec='minutes') if e.stamp else '',row['state'],json.dumps([candidate_data(x) for x in all_candidates],ensure_ascii=False),_selection_label(e,h),int((stamp-e.stamp).total_seconds()) if h else '',int(row['first']),int(row['buro']),' / '.join(x for x in [row.get('reason',''), '更新前に既知の受領記録なし' if row['first'] else '', '更新前にBURO発送・受領記録なし' if row['buro'] else ''] if x),h.own if h else '',q.call if h else e.call,q.date if h else '',q.time if h else '',utc_text(stamp) if h else '',q.band if h else '',q.mode if h else '',q.sent if h else '',q.received if h else '',q.his_qth if h else '',q.my_qth if h else '',q.code if h else '',q.remarks if h else '',row['after'],plan.method,str(h.path) if h else '',h.line if h else '',row['duplicate_of'],status,f.get('backup',''),f.get('before',''),f.get('after','')]
        writer.writerow(dict(zip(COLUMNS,values)))
    return b'\xef\xbb\xbf'+out.getvalue().encode('utf-8')


def _safe_stem(path):
    stem=re.sub(r'[<>:"/\\|?*]+','_',Path(path).stem).strip(' .')
    return stem or 'qsl_receive'

def _human_paths(folder,plan,ident):
    bits=ident.split('-',2);stamp=(bits[0]+'_'+bits[1]) if len(bits)>1 else datetime.now().strftime('%Y%m%d_%H%M%S')
    tail=(bits[2][:6] if len(bits)>2 else uuid.uuid4().hex[:6])
    base=f'{_safe_stem(plan.source)}_{{kind}}_{stamp}_{tail}.txt'
    folder=Path(folder).resolve()
    return folder/base.format(kind='result'),folder/base.format(kind='unprocessed')

def _file_status(row,state):
    hit=row.get('hit')
    if not hit:return ''
    return state.get('files',{}).get(str(hit.path),{}).get('status','')

def row_processed(row,state):
    status=row.get('state','')
    if status in ('既受領スキップ','受領記録済み'):return True
    if status=='更新予定':return _file_status(row,state)=='保存済み'
    if status=='同一交信の重複入力':
        hit=row.get('hit')
        if not hit:return True
        if row.get('after','')==hit.qso.remarks:return True
        return _file_status(row,state)=='保存済み'
    return False

def report_counts(rows,state):
    entries={r['entry'].number for r in rows}
    updated=sum(r.get('state')=='更新予定' and _file_status(r,state)=='保存済み' for r in rows)
    skipped=sum(r.get('state') in ('既受領スキップ','受領記録済み') for r in rows)
    duplicate=sum(r.get('state')=='同一交信の重複入力' and row_processed(r,state) for r in rows)
    grouped={number:[] for number in entries}
    for row in rows:grouped.setdefault(row['entry'].number,[]).append(row)
    unresolved=sum(not group or not all(row_processed(r,state) for r in group) for group in grouped.values())
    return {'input':len(entries),'updated':updated,'skipped':skipped,'duplicate':duplicate,'unprocessed':unresolved}

def _compact_hit(entry,hit):
    q=hit.qso;delta=''
    if entry.stamp:
        stamp=datetime.strptime(q.date+' '+q.time,'%Y-%m-%d %H:%M')
        delta=f' 差{int((stamp-entry.stamp).total_seconds()/60):+d}分'
    diff=call_difference(entry.call,q.call)
    diff='' if diff=='同一コール' else ' / '+diff
    return f'{q.date} {q.time} {q.call} {q.band}/{q.mode}{delta}{diff}'

def _processed_pslog_raw_lines(rows,state):
    """Return actual post-save PSLog source lines for QSL rows updated this run."""
    result=[];seen=set();cache={}
    for row in rows:
        hit=row.get('hit')
        if not hit or row.get('state')!='更新予定' or _file_status(row,state)!='保存済み':continue
        key=(str(hit.path),hit.line)
        if key in seen:continue
        seen.add(key)
        try:
            log=cache.get(str(hit.path))
            if log is None:
                snap=Snapshot.read(hit.path)
                if snap.data is None:continue
                log=parse(snap.data);cache[str(hit.path)]=log
            if 1<=hit.line<=len(log.lines):
                raw=log.lines[hit.line-1].raw.rstrip('\r\n')
                if raw:result.append(raw)
        except (StorageError,OSError):
            continue
    return result


def _human_result_text(plan,rows,state,result_path,unprocessed_path):
    counts=report_counts(rows,state)
    lines=[
        f'PSLog Ver{VERSION} QSL一括受領 処理結果',
        f'処理ID: {state.get("id","")}',
        f'受領方法: {plan.method}',
        f'対象基本コール: {plan.own}',
        f'入力TXT: {plan.source}',
        f'入力 {counts["input"]}件 / 更新 {counts["updated"]}件 / 既受領等スキップ {counts["skipped"]}件 / 重複入力処理済 {counts["duplicate"]}件 / 未処理 {counts["unprocessed"]}件',
        f'結果レポート: {result_path}',
        '未処理(のこり): '+(str(unprocessed_path) if counts['unprocessed'] else '0件（未処理TXTは作成しません）'),
        '',
        '--- 詳細 ---'
    ]
    for row in rows:
        entry=row['entry'];processed=row_processed(row,state);hit=row.get('hit')
        if row.get('state')=='更新予定' and processed:kind='更新'
        elif processed:kind='処理済'
        else:kind='未処理'
        lines.append(f'[{kind}] 入力行{entry.number}: {entry.raw}')
        lines.append(f'  状態: {row.get("state","")}')
        if row.get('reason'):lines.append(f'  理由: {row["reason"]}')
        if hit:
            q=hit.qso;lines.append(f'  QSO: {q.date} {q.time} {q.call} {q.band}/{q.mode}')
            if row.get('after','')!=q.remarks:
                lines.append(f'  RMKS: {q.remarks or "(空欄)"} -> {row.get("after") or "(空欄)"}')
            fs=_file_status(row,state)
            if fs:lines.append(f'  保存状態: {fs}')
        if not processed:
            if entry.nearby:
                lines.append('  同一コールの近いログ: '+_compact_hit(entry,entry.nearby[0]))
            if entry.around:
                lines.append('  入力時刻±3分のQSO:')
                for nearby in entry.around:lines.append('    - '+_compact_hit(entry,nearby))
        lines.append('')
    lines.extend(['===== QSL対象となったPSLog原本行 ====='])
    source_lines=_processed_pslog_raw_lines(rows,state)
    if source_lines:lines.extend(source_lines)
    else:lines.append('（今回、PSLog原本を書き換えたQSOはありません）')
    return '\r\n'.join(lines).rstrip()+ '\r\n'

def _unprocessed_bytes(plan,rows,state):
    grouped={}
    for row in rows:grouped.setdefault(row['entry'].number,[]).append(row)
    pending=[]
    for entry in plan.entries:
        group=grouped.get(entry.number,[])
        if not group or not all(row_processed(r,state) for r in group):pending.append(entry.raw)
    if not pending:return None
    text='\r\n'.join(pending)+'\r\n'
    if plan.encoding=='cp932':return text.encode('cp932')
    return text.encode('utf-8-sig')

def write_human_reports(plan,rows,state,folder,ident):
    result_path,unprocessed_path=_human_paths(folder,plan,ident)
    pending=_unprocessed_bytes(plan,rows,state)
    result_text=_human_result_text(plan,rows,state,result_path,unprocessed_path if pending else None)
    replace_bytes(result_path,result_text.encode('utf-8-sig'),Snapshot(None,None))
    actual_unprocessed=None
    if pending is not None:
        replace_bytes(unprocessed_path,pending,Snapshot(None,None));actual_unprocessed=unprocessed_path
    return result_path,actual_unprocessed

def report_paths(journal):
    try:state=json.loads(Path(journal).read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError):return None,None
    a=state.get('result_report');b=state.get('unprocessed_report')
    return (Path(a) if a else None,Path(b) if b else None)

class BatchFailure(StorageError):
    def __init__(self,message,csv_path,journal,saved,result_report=None,unprocessed_report=None):
        super().__init__(message);self.csv=csv_path;self.journal=journal;self.saved=saved;self.result_report=result_report;self.unprocessed_report=unprocessed_report

def commit(repo,plan,folder):
    if plan.consumed:raise StorageError('処理済みの照合結果です。再照合してください。')
    if not str(folder).strip():raise StorageError('結果CSVの保存先を指定してください。')
    folder=Path(folder).resolve()
    if folder==repo.book or repo.book in folder.parents or folder==repo.root/'config' or repo.root/'config' in folder.parents:
        raise StorageError('結果の保存先はlogbook・config以外にしてください。')
    rows=decisions(plan)
    if not rows:raise StorageError('入力行がありません。')
    targets={}
    for row in rows:
        if row['state']!='更新予定':continue
        h=row['hit'];targets.setdefault(h.path,{'session':h.session,'changes':{}})['changes'][h.line]=row['after']
    for t in targets.values():t['data']=edited_bytes(t['session'],t['changes'])
    ident=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex
    directory=folder/('qsl-'+ident);csv_path=directory/'result.csv';journal=directory/'journal.json'
    digest=lambda b:hashlib.sha256(b).hexdigest()
    state={'id':ident,'source':str(plan.source),'source_sha256':digest(plan.snapshot.data),'method':plan.method,'own':plan.own,'zone':plan.zone,'status':'準備','files':{str(p):{'status':'未処理','before':digest(t['session'].snapshot.data),'after':digest(t['data'])} for p,t in targets.items()}}
    intent=None
    saved=[];expected_csv=Snapshot(None,None);expected_journal=Snapshot(None,None)
    def persist():
        nonlocal expected_csv,expected_journal
        journal_data=json.dumps(state,ensure_ascii=False,indent=2).encode('utf-8');csv_data=csv_bytes(plan,rows,state)
        if intent:intent.allow({journal:journal_data,csv_path:csv_data})
        replace_bytes(journal,journal_data,expected_journal);expected_journal=Snapshot.read(journal)
        replace_bytes(csv_path,csv_data,expected_csv);expected_csv=Snapshot.read(csv_path)
    with operation_lock(repo.book):
        plan.snapshot.check(plan.source)
        if scope_files(repo,plan.own)!=sorted(plan.snapshots):raise ExternalChange('照合後に対象ログが増減しました。再照合してください。')
        for p,snap in plan.snapshots.items():snap.check(p)
        plan.consumed=True
        try:
            persist()  # Results must be durable BEFORE any backup or original mutation.
            for p,t in targets.items():
                state['files'][str(p)]['backup']=str(repo.backup(p,t['session'].snapshot.data))
            persist()
            from batch_recovery import create
            from copy import deepcopy
            final=deepcopy(state);final['status']='完了'
            for f in final['files'].values():f['status']='保存済み'
            intent=create(repo,'qsl',[(p,t['session'].snapshot,t['data']) for p,t in sorted(targets.items())],{journal:json.dumps(final,ensure_ascii=False,indent=2).encode('utf-8'),csv_path:csv_bytes(plan,rows,final)})
            for p,t in sorted(targets.items()):
                f=state['files'][str(p)];f['status']='処理中・成否要確認';persist()
                replace_bytes(p,t['data'],t['session'].snapshot)
                saved.append(p);repo.started.add(p);repo.changed.add(p)
                f['status']='保存済み';persist()
            state['status']='完了';persist()
            result_report,unprocessed_report=write_human_reports(plan,rows,state,folder,ident)
            state['result_report']=str(result_report);state['unprocessed_report']=str(unprocessed_report) if unprocessed_report else ''
            state['report_counts']=report_counts(rows,state);persist()
            intent.finish();intent=None
        except (StorageError,OSError) as e:
            state['status']='停止';state['error']=str(e)
            # An interrupted write may have reached the disk. Inspect bytes, never guess success.
            for p,t in targets.items():
                f=state['files'][str(p)]
                if f['status']=='処理中・成否要確認':
                    try:
                        current=Snapshot.read(p).data
                        if current==t['session'].snapshot.data:f['status']='未保存'
                        elif current==t['data']:f['status']='保存済み';saved.append(p) if p not in saved else None;repo.changed.add(p)
                    except (StorageError,OSError):pass
            try:persist()
            except (StorageError,OSError):pass
            result_report=Path(state['result_report']) if state.get('result_report') else None
            unprocessed_report=Path(state['unprocessed_report']) if state.get('unprocessed_report') else None
            if result_report is None:
                try:
                    result_report,unprocessed_report=write_human_reports(plan,rows,state,folder,ident)
                    state['result_report']=str(result_report);state['unprocessed_report']=str(unprocessed_report) if unprocessed_report else ''
                    state['report_counts']=report_counts(rows,state);persist()
                except (StorageError,OSError):pass
            raise BatchFailure('処理を停止しました。保存済み '+str(len(saved))+'ファイル。結果CSVと回復記録を確認し「ログを再読込」で回復してください。同じ受領一覧を再実行しないでください。\n'+str(e),csv_path,journal,saved,result_report,unprocessed_report) from e
    return csv_path,journal,saved
