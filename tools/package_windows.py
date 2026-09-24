"""Package an already-built PSLog onedir tree as a validated update-capable ZIP."""
import argparse, json, hashlib, platform, sys, zipfile, io
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage import VERSION
from update_package import (
    FORMAT_NAME, FORMAT_VERSION, MANIFEST_PATH, LEGACY_MANIFEST_PATH,
    REQUIRED_MANAGED_ROOTS, LEGACY_MANAGED_ROOTS_1042, LEGACY_MANAGED_ROOTS_1041,
)

REQUIRED=('locations.json','aja_locations.json','club_db.csv','club_db_meta.json','cty.dat','cty_meta.json','cty_LICENSE.txt')
PDFS=('toyama_OSOSUMMARY.pdf','toyama_QSOLOG.pdf')
FORBIDDEN={'conf.cfg','location_overrides.json','submit_profiles.json'}
BUNDLED_DIRS=(Path('config/rules'),Path('config/db/contest'),Path('config/templates/cabrillo'))
RETIRED_ROOT_DOCS=('USER_GUIDE.txt','SAVE_LOCATION.md','WINDOWS_CHECKLIST.txt')


def _source_assets(source):
    source=Path(source)
    assets={Path('config/db')/name:source/'config/db'/name for name in REQUIRED}
    assets.update({Path('config/templates/pdf')/name:source/'config/templates/pdf'/name for name in PDFS})
    for folder in BUNDLED_DIRS:
        root=source/folder
        if not root.is_dir():raise ValueError('配布に必要な初期データフォルダーがありません: '+str(folder))
        for p in root.rglob('*'):
            if p.is_file():assets[p.relative_to(source)]=p
    return assets


def _base_payload(build, source):
    build,source=Path(build),Path(source)
    if build.is_symlink():raise ValueError('配布元にシンボリックリンクは使用できません。')
    exe=build/'pslog.exe';updater=build/'exec'/'PSLogUpdater.exe'
    if not exe.is_file() or exe.read_bytes()[:2]!=b'MZ':raise ValueError('Windowsビルド済みpslog.exeが必要です。')
    if not updater.is_file() or updater.read_bytes()[:2]!=b'MZ':raise ValueError('Windowsビルド済みexec/PSLogUpdater.exeが必要です。')
    source_assets=_source_assets(source)
    for logical,src in source_assets.items():
        if not any((build/prefix/logical).is_file() for prefix in (Path('_internal'),Path('.'))):
            raise ValueError('配布に必要な初期データが不足しています: '+str(logical))

    payload={}
    allowed_top={'_internal','exec','docs','meta'}
    for p in sorted(build.rglob('*')):
        if p.is_symlink():raise ValueError('配布ツリーにシンボリックリンクがあります。')
        if not p.is_file():continue
        rel=p.relative_to(build)
        folded=tuple(part.casefold() for part in rel.parts)
        logical=Path(*rel.parts[1:]) if rel.parts and rel.parts[0]=='_internal' else rel
        if 'config' in folded:
            src=source_assets.get(logical)
            if src is None:
                raise ValueError('配布対象外の設定データがあります: '+str(rel))
            if p.read_bytes()!=src.read_bytes():
                raise ValueError('初期データが配布用ソースと一致しません: '+str(rel))
        if any(part.lower() in {'logbook','bak','output'} for part in rel.parts) or p.name.lower() in FORBIDDEN:
            raise ValueError('利用者データが配布ツリーに含まれています: '+str(rel))
        if len(rel.parts)==1 and rel.name!='pslog.exe':
            raise ValueError('PSLogルートにはpslog.exe以外のファイルを置けません: '+str(rel))
        if len(rel.parts)>1 and rel.parts[0] not in allowed_top:
            raise ValueError('配布ルート直下に未定義のフォルダーがあります: '+rel.parts[0])
        if rel.parts and rel.parts[0]=='meta':
            raise ValueError('metaフォルダーのJSONはパッケージ作成時に生成します: '+str(rel))
        payload[rel.as_posix()]=p.read_bytes()
    return payload, updater


def _legacy_docs(source, payload):
    source=Path(source)
    for name in RETIRED_ROOT_DOCS:
        p=source/name
        if not p.is_file():raise ValueError('旧版更新用の説明書がありません: '+name)
        payload[name]=p.read_bytes()


def package(build,source,output,legacy_bridge=False,bridge_from=None):
    """Create a Windows ZIP.

    bridge_from may be '1.041' or '1.042'.  legacy_bridge=True is retained as
    an alias for the old 1.041 bridge command used by earlier scripts.
    """
    build,source,output=map(Path,(build,source,output))
    if output.resolve().is_relative_to(build.resolve()):
        raise ValueError('出力ZIPは配布元フォルダーの外に指定してください。')
    if legacy_bridge:
        if bridge_from not in (None,'1.041'):
            raise ValueError('legacy_bridge と bridge_from を同時指定できません。')
        bridge_from='1.041'
    if bridge_from not in (None,'1.041','1.042'):
        raise ValueError('bridge_from は 1.041 または 1.042 を指定してください。')

    payload,updater=_base_payload(build,source)
    # meta is generated below; docs/ may contain future packaged documents, but
    # it is intentionally empty in Ver1.043.  Old updaters cannot install the
    # new roots, so bridge payloads omit them and use their exact historical
    # root layout instead.
    if bridge_from:
        payload={k:v for k,v in payload.items() if not (k=='docs' or k.startswith('docs/') or k=='meta' or k.startswith('meta/'))}
        _legacy_docs(source,payload)
        if bridge_from=='1.041':
            payload.pop('exec/PSLogUpdater.exe',None)
            payload['PSLogUpdater.exe']=updater.read_bytes()
            managed_roots=LEGACY_MANAGED_ROOTS_1041
        else:
            managed_roots=LEGACY_MANAGED_ROOTS_1042
        build_info_name='BUILD_INFO.json'
        manifest_path=LEGACY_MANIFEST_PATH
        directory_entries=()
    else:
        managed_roots=REQUIRED_MANAGED_ROOTS
        build_info_name='meta/BUILD_INFO.json'
        manifest_path=MANIFEST_PATH
        # Keep docs visible in a freshly extracted Windows package even while it
        # contains no documents yet.
        directory_entries=('PSLog/docs/',)

    packaged_utc=datetime.now(timezone.utc).isoformat()
    build_info={
        'version':VERSION,
        'built_on':platform.platform(),
        'python':sys.version,
        'packaged_utc':packaged_utc,
        'windows_manual_test':'未確認',
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in sorted(payload.items())},
    }
    payload[build_info_name]=json.dumps(build_info,ensure_ascii=False,indent=2).encode('utf-8')

    hashes={name:hashlib.sha256(data).hexdigest() for name,data in sorted(payload.items())}
    manifest={
        'format':FORMAT_NAME,
        'format_version':FORMAT_VERSION,
        'product':'PSLog',
        'version':VERSION,
        'packaged_utc':packaged_utc,
        'managed_roots':list(managed_roots),
        'preserve':['config/','logbook/','logbook_flr/','bak/','output/'],
        'files':hashes,
    }
    manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')

    def root_present(root):
        if root=='PSLOG_UPDATE_INFO.json':return True
        if root=='docs' and not bridge_from:return True
        if root in payload:return True
        return any(name.startswith(root.rstrip('/') + '/') for name in payload)
    for root in managed_roots:
        if not root_present(root):raise ValueError('更新に必要な配布項目がありません: '+root)

    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for entry in directory_entries:z.writestr(entry,b'')
        for name,data in sorted(payload.items()):z.writestr('PSLog/'+name,data)
        z.writestr(manifest_path,manifest_bytes)
    output.parent.mkdir(parents=True,exist_ok=True)
    f=output.open('xb')
    try:
        with f:f.write(buffer.getvalue())
    except BaseException:
        output.unlink(missing_ok=True);raise
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('build');parser.add_argument('source');parser.add_argument('output')
    parser.add_argument('--legacy-bridge',action='store_true',help='compatibility alias for --bridge-from 1.041')
    parser.add_argument('--bridge-from',choices=('1.041','1.042'))
    args=parser.parse_args()
    print(package(args.build,args.source,args.output,legacy_bridge=args.legacy_bridge,bridge_from=args.bridge_from))
