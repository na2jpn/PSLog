"""PSLog radio information/bridge helpers for Ver1.16.

The radio layer is deliberately optional.  PSLog keeps working when a radio,
pyserial, Hamlib, or the experimental virtual COM provider is unavailable.

Virtual COM relay uses an already-installed com0com ``setupc.exe``.  PSLog
never bundles or silently installs a kernel driver.  A PSLog-managed pair is
created explicitly from the settings screen with Windows administrator approval
and then kept as a persistent virtual cable.  Ordinary PSLog start/stop only
opens or closes the cable; it does not create or delete the Windows COM devices.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json, os, re, shutil, socket, subprocess, tempfile, threading, time

# Same international frequency-to-band ranges used by the ADIF importer.
BAND_RANGES=(
    (0.1357,0.1378,'0.135'),(0.472,0.479,'0.475'),(1.8,2.0,'1.8'),
    (3.5,4.0,'3.5'),(5.06,5.45,'5'),(7.0,7.3,'7'),(10.1,10.15,'10'),
    (14.0,14.35,'14'),(18.068,18.168,'18'),(21.0,21.45,'21'),
    (24.89,24.99,'24'),(28.0,29.7,'28'),(50.0,54.0,'50'),(70.0,71.0,'70'),
    (144.0,148.0,'144'),(222.0,225.0,'222'),(420.0,450.0,'430'),
    (902.0,928.0,'902'),(1240.0,1300.0,'1200'),(2300.0,2450.0,'2400'),
    (3300.0,3500.0,'3300'),(5650.0,5925.0,'5600'),(10000.0,10500.0,'10000'),
    (24000.0,24250.0,'24000'),
 )

# Known radio models are intentionally kept in one small table so the UI can
# present normal model names while the backend still receives CI-V/Hamlib IDs.
# The ICOM addresses and selected Hamlib model IDs follow the PSRTTY 1.14
# reference supplied for this FIX.
ICOM_MODELS={
    'IC-705':0xA4,'IC-7300':0x94,'IC-7300MK2':0xB6,'IC-905':0xAC,
    'IC-7100':0x88,'IC-9700':0xA2,'IC-7610':0x98,'IC-7760':0xB2,
    'IC-7851':0x8E,'IC-7200':0x76,'IC-7410':0x80,'IC-7600':0x7A,
    'IC-9100':0x7C,'IC-756PRO':0x5C,'IC-756PROII':0x64,'IC-756PROIII':0x6E,
    'IC-703':0x68,'IC-7000':0x70,'IC-746':0x56,'IC-7400 / IC-746PRO':0x66,
    'IC-7700':0x74,'IC-7800':0x6A,'IC-910 / IC-910H':0x60,'IC-706':0x48,
    'IC-706MkII':0x4E,'IC-706MkIIG':0x58,'IC-707':0x3E,'IC-78':0x62,
    'IC-718':0x5E,'IC-725':0x28,'IC-726':0x30,'IC-728':0x38,'IC-729':0x3A,
    'IC-735':0x04,'IC-736':0x40,'IC-737':0x3C,'IC-738':0x44,'IC-756':0x50,
    'IC-761':0x1E,'IC-765':0x2C,'IC-775':0x46,'IC-781':0x26,'IC-271':0x20,
    'IC-275':0x10,'IC-375':0x12,'IC-471':0x22,'IC-475':0x14,'IC-575':0x16,
    'IC-820H':0x42,'IC-821H':0x4C,'IC-970':0x2E,'IC-1275':0x18,
}
HAMLIB_MODELS={
    'FT-817 / FT-817ND':1020,'FT-818ND':1041,'FT-857 / FT-857D':1022,
    'FT-991 / FT-991A':1035,'FTX-1':1051,'FT-710':1049,'FTDX10':1042,
    'FTDX101D':1040,'FTDX101MP':1044,'FTDX3000':1037,
    'TS-590SG':2037,'TS-890S':2041,'TS-990S':2039,
}
CUSTOM_ICOM='その他ICOM'
CUSTOM_HAMLIB='その他Hamlib対応機'
AUTO_BAUDS=(115200,57600,38400,19200,9600,4800,2400,1200)

def radio_model_profile(model):
    model=str(model or '').strip()
    if model in ICOM_MODELS:return {'method':'CI-V','civ_address':f'{ICOM_MODELS[model]:02X}','hamlib_model':''}
    if model in HAMLIB_MODELS:return {'method':'Hamlib','civ_address':'','hamlib_model':str(HAMLIB_MODELS[model])}
    if model==CUSTOM_ICOM:return {'method':'CI-V'}
    if model==CUSTOM_HAMLIB:return {'method':'Hamlib'}
    return {}

def infer_radio_model(settings):
    model=str(settings.get('radio_model','') or '').strip()
    if model in ICOM_MODELS or model in HAMLIB_MODELS or model in (CUSTOM_ICOM,CUSTOM_HAMLIB):return model
    method=str(settings.get('radio_method','CI-V'))
    # 1.16 had CI-V address 94 as a generic default.  Do not silently turn a
    # never-configured, disabled installation into an IC-7300 selection.
    if (not settings.get('radio_enabled',False) and method!='Hamlib'
        and str(settings.get('radio_civ_address','94')).strip().upper()=='94'
        and str(settings.get('radio_port','') or '').strip().upper() in ('','AUTO')):
        return ''
    if method=='Hamlib':
        wanted=str(settings.get('radio_hamlib_model','') or '').strip()
        for name,value in HAMLIB_MODELS.items():
            if wanted==str(value):return name
        return CUSTOM_HAMLIB if wanted else ''
    wanted=str(settings.get('radio_civ_address','') or '').strip().upper()
    for name,value in ICOM_MODELS.items():
        if wanted==f'{value:02X}':return name
    return CUSTOM_ICOM if wanted else ''

def normalized_radio_settings(settings):
    result=dict(settings);model=infer_radio_model(result)
    if model:result['radio_model']=model
    profile=radio_model_profile(model)
    if profile:
        result['radio_method']=profile.get('method',result.get('radio_method','CI-V'))
        if 'civ_address' in profile:result['radio_civ_address']=profile['civ_address']
        if 'hamlib_model' in profile:result['radio_hamlib_model']=profile['hamlib_model']
    result['radio_port']=str(result.get('radio_port','AUTO') or 'AUTO').strip() or 'AUTO'
    result['radio_baud']=result.get('radio_baud','AUTO')
    return result


def band_for_frequency_hz(value):
    try: mhz=float(value)/1_000_000.0
    except (TypeError,ValueError): return ''
    return next((band for low,high,band in BAND_RANGES if low<=mhz<=high),'')


def frequency_text(value):
    try:return f'{float(value)/1_000_000.0:.3f}'
    except (TypeError,ValueError):return ''


def append_frequency(existing, value):
    """Append an MHz value with one trailing ASCII space, avoiding exact repeats."""
    token=frequency_text(value)
    if not token:return str(existing or '')
    current=str(existing or '')
    # Ignore trailing whitespace when deciding whether RETURN was pressed twice.
    if current.rstrip().endswith(token):
        return current.rstrip()+' '
    if current and not current[-1].isspace():current+=' '
    return current+token+' '


def list_serial_port_choices():
    try:
        from serial.tools import list_ports
        choices=[]
        for p in list_ports.comports():
            label=p.device
            detail=(getattr(p,'description','') or '').strip()
            if detail and detail.lower() not in ('n/a',p.device.lower()):label+=f' — {detail}'
            choices.append((p.device,label))
        return choices
    except Exception:
        return []

def list_serial_ports():
    return [device for device,_label in list_serial_port_choices()]

def _candidate_ports(value):
    value=str(value or 'AUTO').strip() or 'AUTO'
    return list_serial_ports() if value.upper()=='AUTO' else [value]

def _candidate_bauds(value):
    if str(value).upper()=='AUTO':return list(AUTO_BAUDS)
    try:return [int(value)]
    except (TypeError,ValueError):return []


def _open_serial_safe(serial_module, port, baud, *, timeout=0, write_timeout=1):
    """Open a serial port with hardware PTT control lines deasserted.

    pySerial defaults DTR/RTS to the asserted state.  On radio interfaces where
    DTR or RTS is assigned to SEND/PTT, opening the port with those defaults can
    key the transmitter before PSLog sends any CAT/CI-V command.  Configure the
    line states while the port is still closed, then open it.
    """
    obj=serial_module.Serial()
    try:
        obj.port=port
        obj.baudrate=int(baud)
        obj.timeout=timeout
        obj.write_timeout=write_timeout
        # PSLog uses the serial link for radio information/CAT only.
        # Never use modem control lines as PTT or hardware handshaking.
        obj.rtscts=False
        obj.dsrdtr=False
        try:obj.xonxoff=False
        except Exception:pass
        obj.dtr=False
        obj.rts=False
        obj.open()
        # Re-apply after open as a defensive measure for USB serial drivers.
        # The important part is that the requested states were already False
        # before open(), avoiding pySerial's normal asserted defaults.
        obj.dtr=False
        obj.rts=False
        return obj
    except Exception:
        try:obj.close()
        except Exception:pass
        raise


def _rigctld_command(exe, model, port, baud, tcp_port):
    """Build a receive/control-safe rigctld command for PSLog.

    PSLog does not provide PTT control.  Explicitly disable Hamlib PTT and keep
    DTR/RTS deasserted so opening a configured radio cannot key TX merely by
    starting PSLog.
    """
    return [
        exe,'-m',str(model),'-r',port,'-s',str(baud),'-t',str(tcp_port),
        '-P','NONE','-C','dtr_state=OFF,rts_state=OFF',
    ]


def _com_number(value):
    m=re.fullmatch(r'COM([0-9]+)',str(value or '').strip(),re.I)
    return int(m.group(1)) if m else None


def preferred_virtual_com(physical, busy=()):
    used={int(x) for x in busy}
    base=(_com_number(physical) or 0)+200
    if base<200:base=200
    while base in used:base+=100
    return base


def preferred_virtual_pair(physical, busy=()):
    """Return an external/internal COM pair using the PSLog +200/+100 rule.

    Example: physical COM8 -> COM208 / COM209.  If either port is busy,
    advance both by +100 (COM308 / COM309, ...).
    """
    used={int(x) for x in busy}
    external=preferred_virtual_com(physical,used)
    while external in used or (external+1) in used:
        external+=100
    return external,external+1


def find_rigctld(configured=''):
    candidates=[]
    if configured:candidates.append(Path(configured))
    found=shutil.which('rigctld') or shutil.which('rigctld.exe')
    if found:candidates.append(Path(found))
    if os.name=='nt':
        for root in (os.environ.get('ProgramFiles',''),os.environ.get('ProgramFiles(x86)',''),r'C:\WSJT\wsjtx'):
            if root:
                candidates.extend((Path(root)/'Hamlib'/ 'bin'/'rigctld.exe',Path(root)/'bin'/'rigctld.exe'))
    return str(next((p for p in candidates if p.is_file()),''))


def find_setupc(configured=''):
    candidates=[]
    if configured:candidates.append(Path(configured))
    found=shutil.which('setupc') or shutil.which('setupc.exe')
    if found:candidates.append(Path(found))
    if os.name=='nt':
        for root in (os.environ.get('ProgramFiles',''),os.environ.get('ProgramFiles(x86)','')):
            if root:candidates.append(Path(root)/'com0com'/'setupc.exe')
    return str(next((p for p in candidates if p.is_file()),''))


def _run(args,timeout=20,cwd=None):
    """Run a helper with a hard timeout; helper trouble must never stall PSLog.

    ``cwd`` is used for helpers such as com0com ``setupc.exe`` which resolve
    driver INF files relative to their installation directory.
    """
    try:
        return subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False,cwd=cwd)
    except subprocess.TimeoutExpired as e:
        out=e.stdout.decode(errors='ignore') if isinstance(e.stdout,bytes) else (e.stdout or '')
        err=e.stderr.decode(errors='ignore') if isinstance(e.stderr,bytes) else (e.stderr or '')
        message=(err+' '+f'{timeout}秒でタイムアウトしました。').strip()
        return subprocess.CompletedProcess(args,124,out,message)
    except OSError as e:
        return subprocess.CompletedProcess(args,getattr(e,'winerror',1) or 1,'',str(e))


def _setupc_list(path,timeout=8):
    if not path:return ''
    p=_run([path,'list'],timeout=timeout,cwd=str(Path(path).resolve().parent))
    if p.returncode!=0:
        raise VirtualPortError('com0comの状態確認に失敗しました。'+((p.stdout or '')+' '+(p.stderr or '')).strip())
    return (p.stdout or '')+'\n'+(p.stderr or '')


def _busy_com_numbers(setupc=''):
    busy={n for p in list_serial_ports() if (n:=_com_number(p)) is not None}
    if setupc:
        for m in re.finditer(r'(?:PortName|RealPortName)=COM([0-9]+)',_setupc_list(setupc),re.I):busy.add(int(m.group(1)))
    return busy


def _used_pair_ids(text):
    return {int(x) for x in re.findall(r'\bCNC[AB]([0-9]+)\b',text,re.I)}


@dataclass
class VirtualPair:
    pair_id:int
    external_port:str
    internal_name:str
    setupc:str

    @property
    def internal_path(self):return '\\\\.\\'+self.internal_name


class VirtualPortError(RuntimeError):pass


def _shell_execute_elevated(executable, parameters='', timeout=120, directory=None):
    """Run one Windows process elevated and wait for completion.

    This is used only by the explicit create/delete buttons for the persistent
    com0com pair.  Normal PSLog startup and radio connection never request UAC.
    """
    if os.name!='nt':
        raise VirtualPortError('管理者権限を使う仮想COM操作はWindows版だけで使用できます。')
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_=[
            ('cbSize',wintypes.DWORD),('fMask',wintypes.ULONG),('hwnd',wintypes.HWND),
            ('lpVerb',wintypes.LPCWSTR),('lpFile',wintypes.LPCWSTR),('lpParameters',wintypes.LPCWSTR),
            ('lpDirectory',wintypes.LPCWSTR),('nShow',ctypes.c_int),('hInstApp',wintypes.HINSTANCE),
            ('lpIDList',ctypes.c_void_p),('lpClass',wintypes.LPCWSTR),('hkeyClass',wintypes.HKEY),
            ('dwHotKey',wintypes.DWORD),('hIcon',wintypes.HANDLE),('hProcess',wintypes.HANDLE),
        ]

    SEE_MASK_NOCLOSEPROCESS=0x00000040
    SW_HIDE=0
    WAIT_TIMEOUT=0x00000102
    info=SHELLEXECUTEINFOW()
    info.cbSize=ctypes.sizeof(info);info.fMask=SEE_MASK_NOCLOSEPROCESS
    info.lpVerb='runas';info.lpFile=str(executable);info.lpParameters=str(parameters or '')
    info.lpDirectory=str(directory) if directory else None
    info.nShow=SW_HIDE
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        code=ctypes.windll.kernel32.GetLastError()
        if code==1223:
            raise VirtualPortError('管理者権限の確認がキャンセルされました。')
        raise VirtualPortError(f'管理者権限で操作を開始できませんでした。[WinError {code}]')
    try:
        wait=ctypes.windll.kernel32.WaitForSingleObject(info.hProcess,int(timeout*1000))
        if wait==WAIT_TIMEOUT:
            ctypes.windll.kernel32.TerminateProcess(info.hProcess,124)
            raise VirtualPortError(f'管理者権限での仮想COM操作が{timeout}秒でタイムアウトしました。')
        code=wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess,ctypes.byref(code))
        return int(code.value)
    finally:
        if info.hProcess:ctypes.windll.kernel32.CloseHandle(info.hProcess)


def _ps_quote(value):
    return "'"+str(value).replace("'","''")+"'"


def _run_elevated_setupc_create(tool,external,internal,timeout=120):
    """Create one Ports-class com0com cable with a single UAC prompt.

    setupc is run inside an elevated PowerShell helper. The helper takes its
    own before/after snapshots, finds the newly allocated CNCA/CNCB pair id,
    and assigns both ends a real COM name. This also works when setupc.exe
    itself is configured to always require administrator privileges.

    Returns ``(exit_code, pair_id, detail)``.
    """
    result_fd,result_path=tempfile.mkstemp(prefix='pslog_com0com_result_',suffix='.txt');os.close(result_fd)
    script_fd,script_path=tempfile.mkstemp(prefix='pslog_com0com_',suffix='.ps1');os.close(script_fd)
    result=Path(result_path);script=Path(script_path)
    ps=f'''$ErrorActionPreference = 'Stop'
$tool = {_ps_quote(str(tool))}
$toolDir = Split-Path -Parent $tool
Set-Location -LiteralPath $toolDir
$result = {_ps_quote(str(result))}
$external = {_ps_quote(str(external))}
$internal = {_ps_quote(str(internal))}
function Get-PairIds([string[]]$lines) {{
  $ids = @()
  foreach ($line in $lines) {{
    foreach ($m in [regex]::Matches([string]$line, 'CNC[AB](\\d+)')) {{ $ids += [int]$m.Groups[1].Value }}
  }}
  return @($ids | Sort-Object -Unique)
}}
try {{
  $before = @(& $tool list 2>&1)
  if ($LASTEXITCODE -ne 0) {{ throw ('setupc list(before) failed: ' + ($before -join ' ')) }}
  $beforeIds = @(Get-PairIds $before)
  $install = @(& $tool install 'PortName=COM#' 'PortName=COM#' 2>&1)
  if ($LASTEXITCODE -ne 0) {{ throw ('setupc install failed: ' + ($install -join ' ')) }}
  $pairId = $null
  for ($i=0; $i -lt 40 -and $null -eq $pairId; $i++) {{
    Start-Sleep -Milliseconds 250
    $after = @(& $tool list 2>&1)
    if ($LASTEXITCODE -ne 0) {{ continue }}
    $afterIds = @(Get-PairIds $after)
    $newIds = @($afterIds | Where-Object {{ $beforeIds -notcontains $_ }})
    if ($newIds.Count -ge 1) {{ $pairId = [int]($newIds | Sort-Object | Select-Object -Last 1) }}
  }}
  if ($null -eq $pairId) {{ throw 'new com0com pair id was not detected' }}
  $a = @(& $tool change ("CNCA$pairId") ("RealPortName=$external") 2>&1)
  if ($LASTEXITCODE -ne 0) {{ & $tool remove $pairId | Out-Null; throw ('setupc change A failed: ' + ($a -join ' ')) }}
  $b = @(& $tool change ("CNCB$pairId") ("RealPortName=$internal") 2>&1)
  if ($LASTEXITCODE -ne 0) {{ & $tool remove $pairId | Out-Null; throw ('setupc change B failed: ' + ($b -join ' ')) }}
  Set-Content -LiteralPath $result -Encoding UTF8 -Value ("OK|$pairId")
  exit 0
}} catch {{
  Set-Content -LiteralPath $result -Encoding UTF8 -Value ("ERROR|" + $_.Exception.Message)
  exit 1
}}
'''
    try:
        script.write_text(ps,encoding='utf-8-sig',newline='')
        powershell=shutil.which('powershell.exe') or shutil.which('powershell') or r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
        params=subprocess.list2cmdline(['-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)])
        code=_shell_execute_elevated(powershell,params,timeout=timeout,directory=str(Path(tool).resolve().parent))
        detail=''
        try:detail=result.read_text('utf-8-sig',errors='replace').strip()
        except OSError:pass
        pair_id=None
        if detail.startswith('OK|'):
            try:pair_id=int(detail.split('|',1)[1].strip())
            except (TypeError,ValueError):pair_id=None
        return code,pair_id,detail
    finally:
        for q in (script,result):
            try:q.unlink()
            except OSError:pass


def _run_elevated_setupc_remove(tool,pair_id,timeout=120):
    params=subprocess.list2cmdline(['remove',str(int(pair_id))])
    return _shell_execute_elevated(str(tool),params,timeout=timeout,directory=str(Path(tool).resolve().parent))


class VirtualPortProvider:
    """Persistent com0com cable owned by PSLog.

    The pair is deliberately *not* tied to a PSLog process lifetime.  Creation
    and deletion are explicit administrator operations; ordinary radio connect
    simply opens the existing private side when relay use is enabled.
    """
    def __init__(self,root,setupc=''):
        self.root=Path(root);self.state_path=self.root/'config'/'pslog_virtual_com.json'
        self.setupc=find_setupc(setupc)

    def _save(self,pair):
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        self.state_path.write_text(json.dumps({'persistent':True,'pair_id':pair.pair_id,'external_port':pair.external_port,'internal_name':pair.internal_name,'setupc':pair.setupc},ensure_ascii=False,indent=2),'utf-8')

    def _clear_state(self):
        try:self.state_path.unlink()
        except FileNotFoundError:pass
        except OSError:pass

    def _read_pair(self):
        if not self.state_path.exists():return None
        try:
            data=json.loads(self.state_path.read_text('utf-8'))
            pair_id=int(data['pair_id']);external=str(data.get('external_port','')).strip();internal=str(data.get('internal_name') or f'CNCB{pair_id}').strip()
        except Exception as e:
            raise VirtualPortError('PSLogの仮想COM状態ファイルを解釈できません。削除して作り直してください。') from e
        tool=find_setupc(data.get('setupc','') or self.setupc)
        if not tool:raise VirtualPortError('com0com setupc.exe が見つかりません。無線機設定で場所を指定してください。')
        return VirtualPair(pair_id,external,internal,tool)

    @staticmethod
    def _port_names():
        return {str(x).upper() for x in list_serial_ports()}

    @staticmethod
    def _pair_visible(pair):
        ports=VirtualPortProvider._port_names()
        external=str(pair.external_port or '').upper()
        internal=str(pair.internal_name or '').upper()
        if external not in ports:return False
        if internal.startswith('COM'):return internal in ports
        # Legacy FIX5 state used CNCB<n> for the private side. Keep it readable
        # until the user recreates the pair with FIX7.
        try:
            listing=_setupc_list(pair.setupc)
            return bool(re.search(rf'\b{re.escape(internal)}\b',listing,re.I))
        except Exception:
            return True

    def load_existing(self,verify=True):
        pair=self._read_pair()
        if pair is None:return None
        if verify and not self._pair_visible(pair):
            raise VirtualPortError('保存されているPSLog仮想COMをWindowsで確認できません。「仮想COMを削除」してから作り直してください。')
        return pair

    def status(self):
        if not self.state_path.exists():return None,'未作成'
        try:
            pair=self.load_existing(True)
            return pair,f'常設：{pair.external_port} ⇔ {pair.internal_name}'
        except Exception as e:
            return None,str(e)

    def create_persistent(self,physical):
        if os.name!='nt':raise VirtualPortError('仮想COMはWindows版だけで使用できます。')
        if not self.setupc:raise VirtualPortError('仮想COMにはcom0comが必要です。setupc.exeを指定してください。')
        if self.state_path.exists():
            existing=self.load_existing(True)
            if existing:return existing
        # Do not depend on non-elevated `setupc list`; setupc.exe may itself be
        # configured as "Run as administrator". The Windows COM list is enough
        # for choosing the user-visible pair.
        busy={n for port in list_serial_ports() if (n:=_com_number(port)) is not None}
        external_num,internal_num=preferred_virtual_pair(physical,busy)
        external,internal=f'COM{external_num}',f'COM{internal_num}'
        code,pair_id,detail=_run_elevated_setupc_create(self.setupc,external,internal)
        if code!=0 or pair_id is None:
            reason=detail.split('|',1)[1] if detail.startswith('ERROR|') else detail
            raise VirtualPortError('仮想COMを作成できませんでした。'+((' '+reason) if reason else ' com0comと管理者権限を確認してください。'))
        pair=VirtualPair(pair_id,external,internal,self.setupc)
        deadline=time.monotonic()+15.0
        while time.monotonic()<deadline:
            if self._pair_visible(pair):
                self._save(pair);return pair
            time.sleep(.25)
        raise VirtualPortError(f'仮想COM {external} ⇔ {internal} のWindows登録を15秒以内に確認できませんでした。デバイスマネージャーを確認してください。')

    def remove_persistent(self):
        pair=self.load_existing(False)
        if pair is None:return False,'PSLogの仮想COMは作成されていません。'
        code=_run_elevated_setupc_remove(pair.setupc,pair.pair_id)
        if code!=0:raise VirtualPortError('仮想COMを削除できませんでした。com0comと管理者権限を確認してください。')
        deadline=time.monotonic()+12.0
        while time.monotonic()<deadline:
            if not self._pair_visible(pair):
                self._clear_state();return True,f'{pair.external_port} ⇔ {pair.internal_name} を削除しました。'
            time.sleep(.25)
        raise VirtualPortError('仮想COMの削除後もWindowsにポートが残っています。デバイスマネージャーを確認してください。')


@dataclass
class RadioState:
    connected:bool=False
    frequency_hz:float|None=None
    error:str=''
    virtual_port:str=''
    port:str=''
    baud:int|None=None
    virtual_status:str=''


def parse_civ_frequency(frame):
    """Return Hz from an Icom CI-V frequency frame, or None."""
    data=bytes(frame)
    if len(data)<10 or data[:2]!=b'\xfe\xfe' or data[-1]!=0xfd:return None
    try:cmd=data[4]
    except IndexError:return None
    if cmd not in (0x00,0x03,0x05):return None
    payload=data[5:-1]
    if len(payload)<5:return None
    value=0
    for i,b in enumerate(payload[:5]):
        lo=b&0x0f;hi=(b>>4)&0x0f
        if lo>9 or hi>9:return None
        value+=(lo*10**(2*i))+(hi*10**(2*i+1))
    return float(value)


class _CIVStream:
    def __init__(self):self.buf=bytearray()
    def feed(self,data):
        self.buf.extend(data);frames=[];raw=[]
        while self.buf:
            start=self.buf.find(b'\xfe\xfe')
            if start<0:
                raw.append(bytes(self.buf));self.buf.clear();break
            if start:
                raw.append(bytes(self.buf[:start]));del self.buf[:start]
            end=self.buf.find(b'\xfd',2)
            if end<0:break
            frame=bytes(self.buf[:end+1]);del self.buf[:end+1];frames.append(frame)
        return raw,frames


class RadioManager:
    """Threaded single-radio information source and optional CI-V relay."""
    def __init__(self,root):
        self.root=Path(root);self._lock=threading.Lock();self._state=RadioState();self._stop=threading.Event();self._thread=None;self._pair=None;self._virtual_provider=None

    def state(self):
        with self._lock:return RadioState(self._state.connected,self._state.frequency_hz,self._state.error,self._state.virtual_port,self._state.port,self._state.baud,self._state.virtual_status)

    def is_running(self):
        """True while a radio worker is alive, including connection attempts."""
        return bool(self._thread and self._thread.is_alive())

    def _set(self,**kw):
        with self._lock:
            for k,v in kw.items():setattr(self._state,k,v)

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=3.0)
        self._thread=None
        self._pair=None;self._virtual_provider=None;self._set(connected=False,frequency_hz=None,virtual_port='',port='',baud=None,virtual_status='')

    def configure(self,settings):
        self.stop();self._stop=threading.Event();self._set(error='',connected=False,frequency_hz=None,virtual_port='',port='',baud=None,virtual_status='')
        settings=normalized_radio_settings(settings)
        if not settings.get('radio_enabled',False):return
        if not infer_radio_model(settings):
            self._set(error='無線機が選択されていません。');return
        method=str(settings.get('radio_method','CI-V')).upper()
        target=self._run_civ if method=='CI-V' else self._run_hamlib
        self._thread=threading.Thread(target=target,args=(dict(settings),),name='PSLogRadio',daemon=True);self._thread.start()

    def _probe_civ(self,serial_module,port,baud,rig,timeout=.45):
        obj=None
        try:
            obj=_open_serial_safe(serial_module,port,baud,timeout=.03,write_timeout=.5)
            try:obj.reset_input_buffer()
            except Exception:pass
            obj.write(bytes((0xFE,0xFE,rig,0xE0,0x03,0xFD)))
            stream=_CIVStream();deadline=time.monotonic()+timeout
            while time.monotonic()<deadline and not self._stop.is_set():
                data=obj.read(obj.in_waiting or 1)
                if data:
                    _raw,frames=stream.feed(data)
                    for frame in frames:
                        freq=parse_civ_frequency(frame)
                        if freq is not None:return freq
                time.sleep(.01)
        except Exception:
            return None
        finally:
            if obj:
                try:obj.close()
                except Exception:pass
        return None

    def _resolve_civ(self,serial_module,s,rig):
        ports=_candidate_ports(s.get('radio_port','AUTO'));bauds=_candidate_bauds(s.get('radio_baud','AUTO'))
        if not ports:raise RuntimeError('使用できるCOMポートが見つかりません。')
        if not bauds:raise RuntimeError('通信速度の設定が不正です。')
        explicit_port=str(s.get('radio_port','AUTO')).upper()!='AUTO'
        explicit_baud=str(s.get('radio_baud','AUTO')).upper()!='AUTO'
        if explicit_port and explicit_baud:return ports[0],bauds[0],None
        for port in ports:
            for baud in bauds:
                if self._stop.is_set():raise RuntimeError('接続を中止しました。')
                freq=self._probe_civ(serial_module,port,baud,rig)
                if freq is not None:return port,baud,freq
        raise RuntimeError('AUTO接続で無線機の応答を確認できません。COMポートまたは通信速度を指定して再確認してください。')

    def _run_civ(self,s):
        try:
            import serial
        except Exception:
            self._set(error='pyserialが利用できないため無線機へ接続できません。');return
        try:rig=int(str(s.get('radio_civ_address','94')).strip(),16)
        except ValueError:self._set(error='CI-Vアドレスは16進数2桁で設定してください。');return
        physical=None;virtual=None
        try:
            port,baud,initial_freq=self._resolve_civ(serial,s,rig)
            physical=_open_serial_safe(serial,port,baud,timeout=0,write_timeout=1)
            self._set(port=port,baud=baud,connected=initial_freq is not None,frequency_hz=initial_freq,error='',virtual_status='')

            source=0xE0
            if s.get('radio_virtual_enabled',False):
                self._virtual_provider=VirtualPortProvider(self.root,str(s.get('radio_setupc_path','')))
                try:
                    pair=self._virtual_provider.load_existing(True)
                    if pair is None:
                        self._set(virtual_status='仮想COMが未作成です。設定 → 無線機設定から「仮想COMを作成」を実行してください。')
                    else:
                        virtual=_open_serial_safe(serial,pair.internal_path,baud,timeout=0,write_timeout=1)
                        self._pair=pair;source=0xE1;self._set(virtual_port=pair.external_port,virtual_status='')
                except Exception as e:
                    self._pair=None;virtual=None;source=0xE0
                    self._set(virtual_port='',virtual_status='仮想COM中継を開始できません：'+str(e))

            radio_stream=_CIVStream();client_stream=_CIVStream();last_poll=0.0
            while not self._stop.is_set():
                now=time.monotonic()
                if now-last_poll>=0.75:
                    physical.write(bytes((0xFE,0xFE,rig,source,0x03,0xFD)));last_poll=now
                if virtual:
                    c=virtual.read(virtual.in_waiting or 1)
                    if c:
                        physical.write(c)
                        _raw,frames=client_stream.feed(c)
                        for frame in frames:
                            freq=parse_civ_frequency(frame)
                            if freq is not None:self._set(frequency_hz=freq,connected=True,error='')
                p=physical.read(physical.in_waiting or 1)
                if p:
                    raw,frames=radio_stream.feed(p)
                    if virtual:
                        for piece in raw:
                            if piece:virtual.write(piece)
                    for frame in frames:
                        freq=parse_civ_frequency(frame)
                        if freq is not None:self._set(frequency_hz=freq,connected=True,error='')
                        if virtual and len(frame)>4 and frame[2]==source and frame[3]==rig and frame[4]==0x03:
                            continue
                        if virtual:virtual.write(frame)
                time.sleep(0.01)
        except Exception as e:
            self._set(error='無線機接続: '+str(e),connected=False)
        finally:
            for obj in (virtual,physical):
                if obj:
                    try:obj.close()
                    except Exception:pass
            # The com0com pair is persistent by design.  Closing PSLog only closes
            # the two serial handles; device creation/deletion is an explicit UAC
            # operation from the settings screen.
            self._pair=None;self._virtual_provider=None;self._set(connected=False,virtual_port='',virtual_status='')

    def _open_rigctld(self,exe,model,port,baud,connect_timeout=1.4):
        sock=socket.socket();sock.bind(('127.0.0.1',0));tcp_port=sock.getsockname()[1];sock.close()
        proc=subprocess.Popen(_rigctld_command(exe,model,port,baud,tcp_port),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        server=None;deadline=time.monotonic()+connect_timeout
        while time.monotonic()<deadline and not self._stop.is_set():
            try:server=socket.create_connection(('127.0.0.1',tcp_port),timeout=.35);break
            except OSError:
                if proc.poll() is not None:break
                time.sleep(.08)
        if not server:
            try:proc.terminate();proc.wait(timeout=.5)
            except Exception:
                try:proc.kill()
                except Exception:pass
            return None,None,None
        server.settimeout(.7);file=server.makefile('rwb',buffering=0)
        try:
            file.write(b'f\n');line=file.readline().decode('ascii','ignore').strip();freq=float(line)
            if not freq>0:raise ValueError
        except Exception:
            try:server.close()
            except OSError:pass
            try:proc.terminate();proc.wait(timeout=.5)
            except Exception:
                try:proc.kill()
                except Exception:pass
            return None,None,None
        return server,proc,freq

    def _run_hamlib(self,s):
        if s.get('radio_virtual_enabled',False):
            self._set(error='Ver1.16の仮想COM中継はCI-V接続時だけ使用できます。Hamlibでは仮想COMをOFFにしてください。');return
        exe=find_rigctld(str(s.get('radio_hamlib_path','')))
        try:model=int(str(s.get('radio_hamlib_model','')).strip())
        except ValueError:model=0
        if not exe:self._set(error='rigctld.exeが見つかりません。Hamlibの場所を設定してください。');return
        if model<=0:self._set(error='Hamlibの無線機が選択されていません。');return
        ports=_candidate_ports(s.get('radio_port','AUTO'));bauds=_candidate_bauds(s.get('radio_baud','AUTO'))
        if not ports:self._set(error='使用できるCOMポートが見つかりません。');return
        server=None;proc=None;file=None;chosen=None;initial=None
        try:
            for port in ports:
                for baud in bauds:
                    if self._stop.is_set():return
                    server,proc,initial=self._open_rigctld(exe,model,port,baud)
                    if server:
                        chosen=(port,baud);break
                if server:break
            if not server:raise RuntimeError('Hamlibで無線機の応答を確認できません。COMポートまたは通信速度を指定して再確認してください。')
            port,baud=chosen;self._set(connected=True,error='',frequency_hz=initial,port=port,baud=baud)
            file=server.makefile('rwb',buffering=0)
            while not self._stop.is_set():
                file.write(b'f\n');line=file.readline().decode('ascii','ignore').strip()
                try:self._set(frequency_hz=float(line),connected=True,error='')
                except ValueError:pass
                time.sleep(.75)
        except Exception as e:self._set(error='Hamlib接続: '+str(e),connected=False)
        finally:
            if server:
                try:server.close()
                except OSError:pass
            if proc:
                try:proc.terminate();proc.wait(timeout=2)
                except Exception:
                    try:proc.kill()
                    except Exception:pass
            self._set(connected=False)


def cleanup_stale_virtual(root):
    """Validate the persistent PSLog virtual cable without deleting it."""
    provider=VirtualPortProvider(root,'')
    if not provider.state_path.exists():return ''
    try:
        provider.load_existing(True);return ''
    except Exception as e:
        return 'PSLogの常設仮想COMを確認できません。設定 → 無線機設定で確認してください。\n'+str(e)
