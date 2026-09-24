"""Previewed PS TXT / ADIF / HAMLOG CSV imports with safe QSL merge."""
from dataclasses import dataclass,field
from pathlib import Path
from datetime import datetime
import json,uuid,hashlib
from storage import (Snapshot,parse,duplicate_key,operation_lock,replace_bytes,
                     StorageError,InvalidLog,TERMINATOR)
from model import validate_station
from qsl_marks import TOKEN,METHODS,tokens,change
from remarks_sections import primary

@dataclass
class ImportPlan:
    source: Path
    snapshot: Snapshot
    log: object
    targets: dict
    call: str
    all_add: bool
    exclude_invalid: bool
    metadata: dict = field(default_factory=dict)

class ImportFailure(StorageError):
    def __init__(self,message,report,saved):
        super().__init__(message);self.report=report;self.saved=saved

_RECEIVED={m.casefold():m for m in METHODS}
_WAITING={m[:-2].casefold():m[:-2] for m in METHODS}

def qsl_markers(remarks):
    """Return recognized QSL markers in encounter order, canonicalized."""
    found=[]
    for match in TOKEN.finditer(primary(remarks)):
        raw=match.group();cf=raw.casefold()
        canonical=_RECEIVED.get(cf,_WAITING.get(cf,raw))
        if canonical.casefold() not in {x.casefold() for x in found}:found.append(canonical)
    return found

def merge_qsl_remarks(existing,incoming):
    """Merge only known QSL markers; never replace unrelated RMKS text."""
    result=existing or '';added=[];incoming_marks=qsl_markers(incoming)
    # Received/confirmed states win over their waiting/sent counterpart.
    ordered=[m for m in incoming_marks if m.casefold() in _RECEIVED]+[m for m in incoming_marks if m.casefold() not in _RECEIVED]
    for mark in ordered:
        cf=mark.casefold()
        if cf in _RECEIVED:
            after,_,_=change(result,_RECEIVED[cf])
            if after!=result:
                result=after;added.append(_RECEIVED[cf])
            continue
        current=tokens(result);received=(mark+'.R').casefold()
        if cf in current or received in current:continue
        result+=(' ' if result and not result[-1].isspace() else '')+mark
        added.append(mark)
    return result,added

def prepare(repo,source,call,suffix='',all_add=False,exclude_invalid=False,override_station=False,csv_encoding='cp932',csv_timezone='',csv_century=2000):
    call=validate_station(call,suffix);source=Path(source).resolve();snap=Snapshot.read(source)
    if snap.data is None:raise StorageError('入力ファイルが見つかりません。')
    extension=source.suffix.lower();metadata={}
    if extension in ('.adi','.adif','.adx'):
        from adif_import import convert
        from preferences import validate as validate_preferences
        from storage import load_settings
        from countries import load as load_countries
        assist=validate_preferences(load_settings(repo.root))['location_assist']
        from locations import load as load_locations
        log,records=convert(snap.data,'adx' if extension=='.adx' else 'adi',call,override_station,load_countries(repo.root) if assist else None,load_locations(repo.root) if assist else None)
        metadata={'format':'ADIF','records':records,'notices':[{'record':n.line,'reason':n.reason,'detail':n.raw} for n in log.notices]}
    elif extension=='.csv':
        from hamlog_import import convert
        from locations import load
        from storage import load_settings
        from preferences import validate as validate_preferences
        assist=validate_preferences(load_settings(repo.root))['location_assist']
        from countries import load as load_countries
        log,metadata=convert(snap.data,csv_encoding,csv_timezone,csv_century,load(repo.root) if assist else None,load_countries(repo.root) if assist else None)
    elif extension=='.txt':log=parse(snap.data)
    else:raise StorageError('対応形式はPSログTXT、ADI、ADIF、ADX、HAMLOG CSVです。')
    targets={}
    for _,q in log.records:
        path=repo.path_for(call,suffix,q.date)
        if path==source:raise StorageError('入力ファイルと保存先が同じです。別の入力ファイルを選んでください。')
        if path not in targets:
            session=repo.open(path);session._editable();existing={}
            for line_no,r in session.log.records:existing.setdefault(duplicate_key(r),[]).append((line_no,r))
            targets[path]={'session':session,'records':[],'skipped':0,'keys':set(existing),'existing':existing,
                           'duplicates':[],'duplicate_details':[],'incoming':{},'merges':{},'qsl_merge_events':0}
        t=targets[path];key=duplicate_key(q);is_duplicate=key in t['keys']
        if is_duplicate:
            reason='既存ログ' if key in t['existing'] else '入力ファイル内';t['duplicates'].append((q,reason))
            detail={'q':q,'reason':reason,'incoming_qsl':qsl_markers(q.remarks),'existing_qsl':[],
                    'merged_qsl':[],'merge_note':''}
            if not all_add:
                t['skipped']+=1
                if reason=='既存ログ':
                    matches=t['existing'][key]
                    if len(matches)==1:
                        line_no,old=matches[0];previous=t['merges'].get(line_no);base=previous['after'] if previous else old.remarks
                        detail['existing_qsl']=qsl_markers(base);after,added=merge_qsl_remarks(base,q.remarks)
                        if after!=base:
                            if previous:
                                previous['after']=after
                                for m in added:
                                    if m.casefold() not in {x.casefold() for x in previous['added']}:previous['added'].append(m)
                            else:t['merges'][line_no]={'before':old.remarks,'after':after,'added':list(added),'key':key}
                            t['qsl_merge_events']+=1;detail['merged_qsl']=list(added);detail['merge_note']='既存ログのRMKSへQSL情報をマージ'
                        else:detail['merge_note']='QSL追加なし（既存情報を保持）'
                    else:
                        detail['merge_note']='既存ログに同一キーが複数あるためQSL自動マージなし'
                else:
                    first=t['incoming'][key];detail['existing_qsl']=qsl_markers(first.remarks);after,added=merge_qsl_remarks(first.remarks,q.remarks)
                    if after!=first.remarks:
                        first.remarks=after;t['qsl_merge_events']+=1;detail['merged_qsl']=list(added);detail['merge_note']='先に読み込んだ同一交信へQSL情報をマージ'
                    else:detail['merge_note']='QSL追加なし（先の入力を保持）'
            else:detail['merge_note']='「全て追加」指定のためQSL自動マージなし'
            t['duplicate_details'].append(detail)
        if not all_add and is_duplicate:continue
        t['records'].append(q);t['keys'].add(key)
        if key not in t['existing'] and key not in t['incoming']:t['incoming'][key]=q
    return ImportPlan(source,snap,log,targets,call,all_add,exclude_invalid,metadata)

def _replace_remarks(raw,new_remarks):
    ending='\r\n' if raw.endswith('\r\n') else '\n' if raw.endswith('\n') else '\r' if raw.endswith('\r') else ''
    body=raw[:-len(ending)] if ending else raw;trimmed=body.rstrip()
    if not trimmed.endswith(TERMINATOR):raise StorageError('QSLマージ対象の原本行を安全に更新できません。')
    trailing=body[len(trimmed):];content=trimmed[:-len(TERMINATOR)];parts=content.split('|')
    if len(parts) not in (10,11):raise StorageError('QSLマージ対象の原本行の項目数が不正です。')
    field=parts[9];lead=field[:len(field)-len(field.lstrip())];trail=field[len(field.rstrip()):]
    parts[9]=lead+new_remarks+trail
    return '|'.join(parts)+TERMINATOR+trailing+ending

def rendered_bytes(session,records,merges):
    existing=session.snapshot.data
    if existing is None:prefix=b'\xef\xbb\xbf'
    elif merges:
        text=existing.decode('utf-8-sig');lines=text.splitlines(keepends=True)
        for line_no,info in sorted(merges.items()):
            if not 1<=line_no<=len(lines):raise StorageError('QSLマージ対象行が見つかりません。再度読み込んでください。')
            lines[line_no-1]=_replace_remarks(lines[line_no-1],info['after'])
        prefix=(( '\ufeff' if session.log.bom else '')+''.join(lines)).encode('utf-8')
    else:prefix=existing
    newline=session.log.newline if existing is not None else '\r\n'
    if records:
        if prefix and not prefix.endswith((b'\r',b'\n',b'\xef\xbb\xbf')):prefix+=newline.encode()
        lines=[]
        for q in records:
            values=[q.date,q.time+' JST',q.band,q.mode,q.call,q.sent,q.received,q.his_qth,q.my_qth,q.remarks,q.code]
            lines.append(' | '.join(values)+' '+TERMINATOR)
        prefix+=(''.join(line+newline for line in lines)).encode('utf-8')
    return prefix

def appended_bytes(session,records):
    return rendered_bytes(session,records,{})

def commit(repo,plan,sections_confirmed=False,conversions_confirmed=False):
    if plan.metadata and not conversions_confirmed:raise StorageError('インポートの変換内容を確認してください。')
    if plan.log.issues and not plan.exclude_invalid:raise InvalidLog('要確認行があります。除外を選んで再確認してください。')
    if any('年・運用' in n.reason for n in plan.log.notices) and not sections_confirmed:raise StorageError('運用区切りがあります。全件を指定自局へ取り込むことを確認してください。')
    targets=[(p,t,rendered_bytes(t['session'],t['records'],t['merges'])) for p,t in sorted(plan.targets.items()) if t['records'] or t['merges']]
    if not targets:raise StorageError('追加またはQSLマージする交信がありません。')
    report=repo.bak/('import-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json')
    state={'source':str(plan.source),'own':plan.call,'all_add':plan.all_add,'import_metadata':plan.metadata,
           'excluded_lines':[{'line':i.line,'reason':i.reason} for i in plan.log.issues],
           'source_sha256':hashlib.sha256(plan.snapshot.data).hexdigest(),'status':'prepared',
           'files':[{'path':str(p),'added':len(t['records']),'skipped':t['skipped'],'qsl_merged':len(t['merges']),'status':'pending',
               'before_sha256':hashlib.sha256(t['session'].snapshot.data).hexdigest() if t['session'].snapshot.data is not None else None,
               'after_sha256':hashlib.sha256(data).hexdigest()} for p,t,data in targets]}
    saved=[];intent=None;expected_report=Snapshot(None,None)
    def write_report():
        nonlocal expected_report
        payload=json.dumps(state,ensure_ascii=False,indent=2).encode()
        if intent:intent.allow({report:payload})
        replace_bytes(report,payload,expected_report);expected_report=Snapshot.read(report)
    with operation_lock(repo.book):
        plan.snapshot.check(plan.source)
        for t in plan.targets.values():t['session'].snapshot.check(t['session'].path)
        try:
            write_report()
            for row,(p,t,data) in zip(state['files'],targets):
                backup=repo.backup(p,t['session'].snapshot.data);row['backup']=str(backup) if backup else None
            from batch_recovery import create
            from copy import deepcopy
            final=deepcopy(state);final['status']='completed'
            for row in final['files']:row['status']='saved'
            intent=create(repo,'import',[(p,t['session'].snapshot,data) for p,t,data in targets],{report:json.dumps(final,ensure_ascii=False,indent=2).encode()})
            for row,(p,t,data) in zip(state['files'],targets):
                row['status']='attempting';write_report();replace_bytes(p,data,t['session'].snapshot)
                saved.append(p);repo.started.add(p);repo.changed.add(p);row['status']='saved';write_report()
            state['status']='completed';write_report();intent.finish()
        except (StorageError,OSError) as e:
            state['status']='interrupted';state['error']=str(e)
            try:write_report()
            except (StorageError,OSError):pass
            raise ImportFailure(f'取り込みを停止しました。保存済み {len(saved)}ファイル。結果を確認し「ログを再読込」で回復してください。同じインポートを再実行しないでください。\n{e}',report,saved) from e
    return report,saved
