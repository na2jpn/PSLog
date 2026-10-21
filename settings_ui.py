from PySide6.QtCore import QTimer
import queue, threading
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QWidget,QCheckBox,QLabel,QComboBox,QFormLayout,QLineEdit,QPushButton,QFileDialog,QGroupBox,QSpinBox
from preferences import DEFAULTS,validate
from search_ui import button
from storage import StorageError, VERSION

from window_geometry import SafeDialog as QDialog

class SettingsDialog(QDialog):
    def __init__(self,values,apply,parent=None,repo=None,initial_tab=None):
        super().__init__(parent);self.values=validate(values);self.apply_callback=apply;self.repo=repo;self.initial_tab=initial_tab
        self.setWindowTitle(f'PSLog {VERSION} — '+('無線機設定' if initial_tab=='無線機設定' else '設定'));self.resize(760,540)
        outer=QVBoxLayout(self);tabs=QTabWidget();self.tabs=tabs;outer.addWidget(tabs,1);self.checks={}
        input_page=QWidget();form=QVBoxLayout(input_page);tabs.addTab(input_page,'入力補助')
        for key,label in [('keep_band','新しい交信でもBANDを維持する'),('keep_mode','新しい交信でもMODEを維持する'),('auto_rst','モードに応じてRSTを自動入力する'),('confirm_record','記録前の確認を表示する'),('location_assist','所在地の入力補助を使う')]:
            cb=QCheckBox(label);cb.setChecked(self.values[key]);self.checks[key]=cb;form.addWidget(cb)
        text=QLabel('SSB / FM / AM：59　　CW / RTTY：599\nSSTV：595　　FT8 / FT4 / FT2：-01　　FreeDV：+00\nサブモードを含む表記にも適用します。\n\nコールサイン・MY QTHは直近の入力値を引き継ぎます。\n所在地は確認済みの表記と、ログ由来の未確認候補を区別します。');text.setWordWrap(True);form.addWidget(text);form.addStretch()

        radio_page=QWidget();radio_root=QVBoxLayout(radio_page);tabs.addTab(radio_page,'無線機設定')
        radio_intro=QLabel('PSLogは無線機を1台接続し、周波数情報を取得します。通常は無線機・COMポート・通信速度を選ぶだけです。\n設定済みなら起動時に自動接続し、接続できなくてもPSLogのログ機能は通常どおり使用できます。')
        radio_intro.setWordWrap(True);radio_intro.setStyleSheet('color:#55636c;');radio_root.addWidget(radio_intro)
        basic=QGroupBox('無線機');rf=QFormLayout(basic);rf.setVerticalSpacing(8);radio_root.addWidget(basic)
        self.radio_enabled=QCheckBox('無線機接続を使用する');self.radio_enabled.setChecked(self.values['radio_enabled']);rf.addRow(self.radio_enabled)
        from radio_control import ICOM_MODELS,HAMLIB_MODELS,CUSTOM_ICOM,CUSTOM_HAMLIB,infer_radio_model
        self.radio_model=QComboBox();self.radio_model.addItem('選択してください','')
        for name in ICOM_MODELS:self.radio_model.addItem('ICOM  '+name,name)
        self.radio_model.addItem('ICOM  その他ICOM',CUSTOM_ICOM)
        for name in HAMLIB_MODELS:self.radio_model.addItem(('KENWOOD  ' if name.startswith('TS-') else 'YAESU  ')+name,name)
        self.radio_model.addItem('Hamlib  その他対応機',CUSTOM_HAMLIB)
        selected=infer_radio_model(self.values);idx=self.radio_model.findData(selected);self.radio_model.setCurrentIndex(idx if idx>=0 else 0);rf.addRow('無線機',self.radio_model)
        port_host=QWidget();pr=QHBoxLayout(port_host);pr.setContentsMargins(0,0,0,0);self.radio_port=QComboBox();pr.addWidget(self.radio_port,1);refresh=QPushButton('再読込');pr.addWidget(refresh);rf.addRow('COMポート',port_host)
        refresh.clicked.connect(self._reload_radio_ports);self._reload_radio_ports(self.values.get('radio_port','AUTO'))
        self.radio_baud=QComboBox();self.radio_baud.addItem('AUTO','AUTO')
        for value in (115200,57600,38400,19200,9600,4800,2400,1200):self.radio_baud.addItem(str(value),value)
        target_baud=self.values.get('radio_baud','AUTO');idx=self.radio_baud.findData(target_baud);self.radio_baud.setCurrentIndex(idx if idx>=0 else 0);rf.addRow('通信速度',self.radio_baud)
        self.radio_method_label=QLabel();rf.addRow('接続方式',self.radio_method_label)
        self.radio_detail=QGroupBox('機種固有設定');df=QFormLayout(self.radio_detail);radio_root.addWidget(self.radio_detail)
        self.radio_civ_label=QLabel('CI-Vアドレス（16進）');self.radio_civ=QLineEdit(self.values['radio_civ_address']);self.radio_civ.setPlaceholderText('例：A4');df.addRow(self.radio_civ_label,self.radio_civ)
        self.radio_hamlib_label=QLabel('Hamlib Model ID');self.radio_hamlib_model=QLineEdit(self.values['radio_hamlib_model']);self.radio_hamlib_model.setPlaceholderText('Hamlib Model ID');df.addRow(self.radio_hamlib_label,self.radio_hamlib_model)
        self.rig_host=QWidget();rr=QHBoxLayout(self.rig_host);rr.setContentsMargins(0,0,0,0);self.radio_hamlib_path=QLineEdit(self.values['radio_hamlib_path']);rr.addWidget(self.radio_hamlib_path,1);rb=QPushButton('参照…');rr.addWidget(rb);self.rig_path_label=QLabel('rigctld.exe');df.addRow(self.rig_path_label,self.rig_host)
        rb.clicked.connect(lambda:self.radio_hamlib_path.setText(QFileDialog.getOpenFileName(self,'rigctld.exeを選択',self.radio_hamlib_path.text() or '', '実行ファイル (*.exe);;すべてのファイル (*)')[0] or self.radio_hamlib_path.text()))
        self.radio_detail_note=QLabel();self.radio_detail_note.setWordWrap(True);self.radio_detail_note.setStyleSheet('color:#55636c;');df.addRow(self.radio_detail_note)
        control_row=QHBoxLayout();self.radio_test=QPushButton('接続テスト');self.radio_test.clicked.connect(self._test_radio);control_row.addWidget(self.radio_test);self.radio_connect=QPushButton('接続');self.radio_connect.clicked.connect(self._toggle_radio_connection);control_row.addWidget(self.radio_connect);self.radio_test_status=QLabel('');self.radio_test_status.setWordWrap(True);control_row.addWidget(self.radio_test_status,1);radio_root.addLayout(control_row)
        test_note=QLabel('「接続テスト」は設定を保存せず最大10秒だけ確認します。「接続」は現在の設定を保存して通常接続を開始します。切断しても設定は残り、次回起動時は自動接続します。')
        test_note.setWordWrap(True);test_note.setStyleSheet('color:#55636c;');radio_root.addWidget(test_note);radio_root.addStretch(1)

        virtual_page=QWidget();virtual_root=QVBoxLayout(virtual_page);tabs.addTab(virtual_page,'仮想COM中継')
        virtual_intro=QLabel('WSJT-Xなど外部ソフトをPSLog経由で無線機へ接続するための追加機能です。使わない場合は設定不要です。\nVer1.16ではCI-V接続時のみ使用できます。')
        virtual_intro.setWordWrap(True);virtual_intro.setStyleSheet('color:#55636c;');virtual_root.addWidget(virtual_intro)
        virtual=QGroupBox('仮想COM中継（試験機能）');vf=QFormLayout(virtual);virtual_root.addWidget(virtual)
        self.radio_virtual=QCheckBox('仮想COM中継を使用する');self.radio_virtual.setChecked(self.values['radio_virtual_enabled']);vf.addRow(self.radio_virtual)
        self.virtual_status=QLabel();self.virtual_status.setWordWrap(True);vf.addRow('状態',self.virtual_status)
        setup_host=QWidget();sr=QHBoxLayout(setup_host);sr.setContentsMargins(0,0,0,0);self.radio_setupc=QLineEdit(self.values['radio_setupc_path']);self.radio_setupc.setPlaceholderText(r'例：C:\Program Files (x86)\com0com\setupc.exe');sr.addWidget(self.radio_setupc,1);sb=QPushButton('参照…');sr.addWidget(sb);vf.addRow('com0com setupc.exe',setup_host)
        sb.clicked.connect(lambda:self.radio_setupc.setText(QFileDialog.getOpenFileName(self,'setupc.exeを選択',self.radio_setupc.text() or '', '実行ファイル (*.exe);;すべてのファイル (*)')[0] or self.radio_setupc.text()))
        virtual_note=QLabel('com0comをインストール済みの場合はsetupc.exeを自動検出します。見つからない場合だけ「参照…」で指定してください。\n例：C:\\Program Files\\com0com\\setupc.exe\n　　C:\\Program Files (x86)\\com0com\\setupc.exe\n作成時は外部ソフト用とPSLog内部用の2つを通常のCOMポートとして作成します（例：COM208 ⇔ COM209）。')
        virtual_note.setWordWrap(True);virtual_note.setStyleSheet('color:#55636c;');vf.addRow(virtual_note)
        virtual_link=QLabel('<a href="https://sourceforge.net/projects/com0com/">com0com 公式配布ページ（SourceForge）を開く</a>');virtual_link.setOpenExternalLinks(True);vf.addRow('',virtual_link)
        virtual_buttons=QHBoxLayout();self.virtual_create=QPushButton('仮想COMを作成');self.virtual_create.clicked.connect(self._create_virtual_pair);virtual_buttons.addWidget(self.virtual_create);self.virtual_delete=QPushButton('仮想COMを削除');self.virtual_delete.clicked.connect(self._delete_virtual_pair);virtual_buttons.addWidget(self.virtual_delete);virtual_buttons.addStretch();vf.addRow('',virtual_buttons)
        persistent_note=QLabel('仮想COMの作成・削除時だけWindowsの管理者権限（UAC）が必要です。作成した仮想COMは常設し、PSLogを終了しても削除しません。通常の接続／切断では中継だけを開始・停止します。')
        persistent_note.setWordWrap(True);persistent_note.setStyleSheet('color:#55636c;');vf.addRow('',persistent_note)
        virtual_control=QHBoxLayout();self.virtual_radio_connect=QPushButton('接続');self.virtual_radio_connect.clicked.connect(self._toggle_radio_connection);virtual_control.addWidget(self.virtual_radio_connect);self.virtual_connection_status=QLabel('');self.virtual_connection_status.setWordWrap(True);virtual_control.addWidget(self.virtual_connection_status,1);virtual_root.addLayout(virtual_control)
        virtual_connect_note=QLabel('ここからの「接続／切断」も無線機設定タブと同じ接続を操作します。仮想COMが作成済みで「仮想COM中継を使用する」がONなら、中継も同時に開始します。')
        virtual_connect_note.setWordWrap(True);virtual_connect_note.setStyleSheet('color:#55636c;');virtual_root.addWidget(virtual_connect_note);virtual_root.addStretch(1)
        self._radio_test_manager=None;self._radio_test_deadline=0.0;self._resume_parent_after_test=False;self._radio_test_timer=QTimer(self);self._radio_test_timer.setInterval(150);self._radio_test_timer.timeout.connect(self._poll_radio_test)
        self._virtual_op_queue=queue.Queue();self._virtual_op_thread=None;self._virtual_op_timer=QTimer(self);self._virtual_op_timer.setInterval(150);self._virtual_op_timer.timeout.connect(self._poll_virtual_operation)
        self._radio_status_timer=QTimer(self);self._radio_status_timer.setInterval(300);self._radio_status_timer.timeout.connect(self._refresh_connection_status);self._radio_status_timer.start()
        self.radio_model.currentIndexChanged.connect(self._radio_mode_changed);self.radio_enabled.toggled.connect(self._radio_mode_changed);self.radio_virtual.toggled.connect(self._radio_mode_changed);self._radio_mode_changed()

        backup_page=QWidget();form=QFormLayout(backup_page);form.setVerticalSpacing(9);tabs.addTab(backup_page,'バックアップ')
        text=QLabel('自動バックアップ：有効\nログを書き換える前、編集・削除・復元の前、変更がある状態で終了するときに、元のログを自動で保護します。\n前回と内容が同じ場合は、同じバックアップを重複して作成しません。');text.setWordWrap(True);form.addRow(text)
        self.keep=QComboBox();self.keep.addItems(['10','30','60','100']);self.keep.setCurrentText(str(self.values['backup_keep']))
        keep_row=QWidget();kr=QHBoxLayout(keep_row);kr.setContentsMargins(0,0,0,0);kr.addWidget(self.keep);kr.addWidget(QLabel('件'));kr.addStretch();form.addRow('バックアップ保持数（ログ・履歴）',keep_row)
        keep_help=QLabel('ログごと、および完了済み回復記録・変更履歴の種類ごとにこの件数を保持します。起動・終了時と正常な保存後に古いものを整理します。全体復元前の安全ZIPは直近2世代。未完了記録・復旧失敗の記録・任意の場所へ手動保存した全体バックアップZIPは自動削除しません。');keep_help.setWordWrap(True);keep_help.setStyleSheet('color:#55636c;');form.addRow('',keep_help)
        if self.repo is not None:
            path=QLineEdit(str(self.repo.bak));path.setReadOnly(True);path.setToolTip(str(self.repo.bak));form.addRow('自動バックアップ保存先',path)
            files=sorted(self.repo.bak.glob('*.bak')) if self.repo.bak.exists() else []
            sources={f.name.split('.',1)[0] for f in files}
            latest='なし'
            if files:
                try: latest=max(files,key=lambda x:x.stat().st_mtime).stat().st_mtime
                except OSError: latest=None
                if latest is not None:
                    from datetime import datetime
                    latest=datetime.fromtimestamp(latest).strftime('%Y/%m/%d %H:%M:%S')
                else: latest='確認できません'
            current=QLabel(f'現在の自動ログバックアップ：{len(files)}件（{len(sources)}ログ）\n最新バックアップ：{latest}')
            current.setWordWrap(True);form.addRow('現在の状態',current)
        cb=QCheckBox('月が替わったら全体バックアップを案内する');cb.setChecked(self.values['monthly_backup']);self.checks['monthly_backup']=cb;form.addRow(cb)
        text=QLabel('月替わりの案内は、自動で全体バックアップを作る機能ではありません。\n案内から「今すぐ作成」を選ぶと、logbook と config を1つのZIPにまとめ、別ドライブやUSBメモリーなど、任意の場所へ保存できます。');text.setWordWrap(True);form.addRow(text)
        from alert_audio import AlertPlayer,SOUNDS
        self.alert_player=AlertPlayer(self)
        audio=QWidget();af=QFormLayout(audio);tabs.addTab(audio,'通知音')
        self.alert_volume=QSpinBox();self.alert_volume.setRange(0,100);self.alert_volume.setSuffix(' %');self.alert_volume.setValue(self.values['alert_volume']);af.addRow('アプリの通知音量',self.alert_volume)
        self.alert_sound=QComboBox()
        for ident,label in SOUNDS:self.alert_sound.addItem(label,ident)
        self.alert_sound.setCurrentIndex(self.alert_sound.findData(self.values['alert_sound']));af.addRow('アラート音',self.alert_sound)
        preview=QPushButton('音を確認');preview.clicked.connect(self._preview_alert);af.addRow(preview)
        af.addRow(QLabel('0%で消音。PC本体の音量・消音設定も反映されます。\nクラスタ監視の音ON/OFFは監視画面で切り替えます。'))
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        row=QHBoxLayout();row.addStretch();row.addWidget(button('保存',self.save));row.addWidget(button('キャンセル',self.reject));outer.addLayout(row)
        if initial_tab:
            for i in range(tabs.count()):
                if tabs.tabText(i)==initial_tab:tabs.setCurrentIndex(i);break
        self._refresh_connection_status()
    def _reload_radio_ports(self,selected=None):
        from radio_control import list_serial_port_choices
        if selected is None:selected=self.radio_port.currentData() or self.radio_port.currentText() or 'AUTO'
        selected=str(selected or 'AUTO')
        self.radio_port.clear();self.radio_port.addItem('AUTO','AUTO')
        for device,label in list_serial_port_choices():self.radio_port.addItem(label,device)
        idx=self.radio_port.findData(selected)
        if idx<0 and selected.upper()!='AUTO':
            self.radio_port.addItem(selected+'（未検出）',selected);idx=self.radio_port.count()-1
        self.radio_port.setCurrentIndex(idx if idx>=0 else 0)

    def _radio_mode_changed(self,*_):
        from radio_control import ICOM_MODELS,HAMLIB_MODELS,CUSTOM_ICOM,CUSTOM_HAMLIB,radio_model_profile,find_rigctld,find_setupc
        model=self.radio_model.currentData() or '';profile=radio_model_profile(model);method=profile.get('method','')
        enabled=self.radio_enabled.isChecked();self.radio_model.setEnabled(enabled);self.radio_port.setEnabled(enabled);self.radio_baud.setEnabled(enabled);self.radio_test.setEnabled(enabled and bool(model) and self._radio_test_manager is None)
        if hasattr(self,'radio_connect'):self.radio_connect.setEnabled(enabled and bool(model) and self._radio_test_manager is None)
        if hasattr(self,'virtual_radio_connect'):self.virtual_radio_connect.setEnabled(enabled and bool(model) and self._radio_test_manager is None)
        self.radio_method_label.setText(method or '—')
        if model in ICOM_MODELS:
            self.radio_civ.setText(profile['civ_address']);self.radio_civ.setReadOnly(True)
            self.radio_detail_note.setText(f'CI-Vアドレス {profile["civ_address"]} は選択した機種から自動設定します。')
        else:self.radio_civ.setReadOnly(False)
        if model in HAMLIB_MODELS:
            self.radio_hamlib_model.setText(profile['hamlib_model']);self.radio_hamlib_model.setReadOnly(True)
            self.radio_detail_note.setText('Hamlib Model ID は選択した機種から自動設定します。rigctld.exeは通常、自動検出します。')
        else:self.radio_hamlib_model.setReadOnly(False)
        civ_custom=model==CUSTOM_ICOM;ham_custom=model==CUSTOM_HAMLIB;ham=method=='Hamlib';civ=method=='CI-V'
        if civ_custom:self.radio_detail_note.setText('一覧にないICOM機はCI-Vアドレスを指定してください。')
        elif ham_custom:self.radio_detail_note.setText('一覧にないHamlib対応機はModel IDを指定してください。')
        elif not model:self.radio_detail_note.setText('無線機を選択すると必要な設定だけを表示します。')
        self.radio_civ_label.setVisible(civ_custom);self.radio_civ.setVisible(civ_custom)
        self.radio_hamlib_label.setVisible(ham_custom);self.radio_hamlib_model.setVisible(ham_custom)
        self.radio_detail.setEnabled(enabled and bool(model))
        self.rig_path_label.setVisible(ham);self.rig_host.setVisible(ham);self.radio_hamlib_path.setEnabled(enabled and ham);self.radio_virtual.setEnabled(enabled and civ);self.radio_setupc.setEnabled(enabled and civ and self.radio_virtual.isChecked())
        if ham and not self.radio_hamlib_path.text():
            found=find_rigctld('')
            if found:self.radio_hamlib_path.setText(found)
        if civ and not self.radio_setupc.text():
            found=find_setupc('')
            if found:self.radio_setupc.setText(found)
            else:self.radio_setupc.setPlaceholderText(r'例：C:\Program Files (x86)\com0com\setupc.exe')
        state=getattr(self.parent(),'radio_manager',None).state() if self.parent() is not None and hasattr(self.parent(),'radio_manager') else None
        if state and state.virtual_port:
            self.virtual_status.setText(f'中継中：{state.virtual_port}（物理 {state.port or "COM"}）')
        elif civ:
            from radio_control import VirtualPortProvider
            parent=self.parent();root=self.repo.root if self.repo is not None else getattr(parent,'data_root','.')
            provider=VirtualPortProvider(root,self.radio_setupc.text().strip())
            _pair,status=provider.status();self.virtual_status.setText(status if status else '未作成')
        else:self.virtual_status.setText('Hamlib接続では使用できません。')
        busy=bool(getattr(self,'_virtual_op_thread',None) and self._virtual_op_thread.is_alive())
        can_manage=enabled and civ and bool(self.radio_setupc.text().strip()) and not busy
        self.virtual_create.setEnabled(can_manage);self.virtual_delete.setEnabled(can_manage)

    def _virtual_physical_port(self):
        parent=self.parent();manager=getattr(parent,'radio_manager',None) if parent is not None else None
        if manager:
            state=manager.state()
            if state.port:return state.port
        selected=str(self.radio_port.currentData() or '').strip()
        return '' if selected.upper() in ('','AUTO') else selected

    def _start_virtual_operation(self,action):
        if self._virtual_op_thread and self._virtual_op_thread.is_alive():return
        parent=self.parent();manager=getattr(parent,'radio_manager',None) if parent is not None else None
        if manager and manager.is_running():
            self.virtual_status.setText('仮想COMを作成・削除する前に無線機を「切断」してください。');return
        setupc=self.radio_setupc.text().strip()
        if not setupc:
            self.virtual_status.setText('com0com setupc.exe を指定してください。');return
        physical=self._virtual_physical_port()
        if action=='create' and not physical:
            self.virtual_status.setText('COMポートがAUTOの場合は、先に接続して実COMを確認するか、COMポートを指定してから仮想COMを作成してください。');return
        self.virtual_create.setEnabled(False);self.virtual_delete.setEnabled(False)
        self.virtual_status.setText('仮想COMを作成中… 管理者権限の確認に応答してください。' if action=='create' else '仮想COMを削除中… 管理者権限の確認に応答してください。')
        root=self.repo.root if self.repo is not None else getattr(parent,'data_root','.')
        q=self._virtual_op_queue
        def worker():
            try:
                from radio_control import VirtualPortProvider
                provider=VirtualPortProvider(root,setupc)
                if action=='create':
                    pair=provider.create_persistent(physical);q.put(('ok',f'作成しました：外部ソフトは {pair.external_port} を選択してください。'))
                else:
                    _ok,message=provider.remove_persistent();q.put(('ok',message))
            except Exception as e:q.put(('error',str(e)))
        self._virtual_op_thread=threading.Thread(target=worker,name='PSLogVirtualCOMAdmin',daemon=True);self._virtual_op_thread.start();self._virtual_op_timer.start()

    def _create_virtual_pair(self):
        self._start_virtual_operation('create')

    def _delete_virtual_pair(self):
        self._start_virtual_operation('delete')

    def _poll_virtual_operation(self):
        try:status,message=self._virtual_op_queue.get_nowait()
        except queue.Empty:
            if self._virtual_op_thread and not self._virtual_op_thread.is_alive():
                self._virtual_op_timer.stop();self._virtual_op_thread=None;self._radio_mode_changed()
            return
        self._virtual_op_timer.stop();self._virtual_op_thread=None
        self.virtual_status.setText(message if status=='ok' else '仮想COM操作に失敗しました：'+message)
        self._radio_mode_changed()

    def _radio_values(self):
        from radio_control import radio_model_profile
        model=self.radio_model.currentData() or '';profile=radio_model_profile(model);method=profile.get('method',self.values.get('radio_method','CI-V'))
        civ=profile.get('civ_address',self.radio_civ.text().strip().upper())
        ham=profile.get('hamlib_model',self.radio_hamlib_model.text().strip())
        return dict(radio_enabled=self.radio_enabled.isChecked(),radio_model=model,radio_method=method,radio_port=self.radio_port.currentData() or 'AUTO',radio_baud=self.radio_baud.currentData(),radio_civ_address=civ,radio_hamlib_model=ham,radio_hamlib_path=self.radio_hamlib_path.text().strip(),radio_virtual_enabled=self.radio_virtual.isChecked() if method=='CI-V' else False,radio_setupc_path=self.radio_setupc.text().strip())

    def _test_radio(self):
        if self._radio_test_manager is not None:return
        values=dict(self.values);values.update(self._radio_values());values['radio_enabled']=True;values['radio_virtual_enabled']=False
        try:values=validate(values)
        except ValueError as e:self.radio_test_status.setText(str(e));return
        if not values.get('radio_model'):
            self.radio_test_status.setText('無線機を選択してください。');return
        parent=self.parent()
        if parent is not None and hasattr(parent,'radio_manager'):
            self._resume_parent_after_test=parent.radio_manager.is_running();parent.radio_manager.stop()
        from radio_control import RadioManager
        root=self.repo.root if self.repo is not None else getattr(parent,'data_root','.')
        self._radio_test_manager=RadioManager(root);self._radio_test_deadline=__import__('time').monotonic()+10.0
        self.radio_test.setEnabled(False);self.radio_test_status.setText('接続テスト中…');self._radio_test_manager.configure(values);self._radio_test_timer.start()

    def _poll_radio_test(self):
        if self._radio_test_manager is None:return
        import time
        state=self._radio_test_manager.state()
        if state.connected and state.frequency_hz:
            from radio_control import frequency_text
            self._finish_radio_test(f'接続しました　{state.port or "COM"} / {state.baud or "AUTO"} bps　{frequency_text(state.frequency_hz)} MHz');return
        if state.error:
            self._finish_radio_test(state.error);return
        if time.monotonic()>=self._radio_test_deadline:self._finish_radio_test('接続テストが10秒でタイムアウトしました。COMポート、通信速度、無線機設定を確認してください。')

    def _finish_radio_test(self,message=''):
        self._radio_test_timer.stop()
        if self._radio_test_manager is not None:
            self._radio_test_manager.stop();self._radio_test_manager=None
        self.radio_test_status.setText(message);self.radio_test.setEnabled(self.radio_enabled.isChecked() and bool(self.radio_model.currentData()))
        parent=self.parent()
        if self._resume_parent_after_test and parent is not None and hasattr(parent,'radio_manager'):parent.radio_manager.configure(parent.settings)
        self._resume_parent_after_test=False;self._refresh_connection_status()

    def _refresh_connection_status(self):
        if not hasattr(self,'radio_connect'):return
        parent=self.parent();manager=getattr(parent,'radio_manager',None) if parent is not None else None
        running=bool(manager and manager.is_running());state=manager.state() if manager else None
        label='切断' if running else '接続'
        self.radio_connect.setText(label)
        if hasattr(self,'virtual_radio_connect'):self.virtual_radio_connect.setText(label)
        enabled=self.radio_enabled.isChecked() and bool(self.radio_model.currentData()) and self._radio_test_manager is None
        self.radio_connect.setEnabled(enabled or running)
        if hasattr(self,'virtual_radio_connect'):self.virtual_radio_connect.setEnabled(enabled or running)
        message=''
        if running and state:
            from radio_control import frequency_text
            if state.connected and state.frequency_hz:
                suffix=(' / 仮想 '+state.virtual_port) if state.virtual_port else ''
                if state.virtual_status:suffix+=' / '+state.virtual_status
                message=f'接続中　{state.port or "COM"} / {state.baud or "AUTO"} bps　{frequency_text(state.frequency_hz)} MHz'+suffix
            elif state.error:message=state.error
            else:message='接続中…'
        self.radio_test_status.setText(message)
        if hasattr(self,'virtual_connection_status'):self.virtual_connection_status.setText(message)

    def _toggle_radio_connection(self):
        parent=self.parent();manager=getattr(parent,'radio_manager',None) if parent is not None else None
        if manager and manager.is_running():
            manager.stop();self.radio_test_status.setText('切断しました。');self._refresh_connection_status();return
        values=dict(self.values);values.update({k:cb.isChecked() for k,cb in self.checks.items()});values['backup_keep']=int(self.keep.currentText());values.update(self._radio_values())
        if not values.get('radio_enabled'):
            self.radio_test_status.setText('「無線機接続を使用する」をONにしてください。');return
        if not values.get('radio_model'):
            self.radio_test_status.setText('無線機を選択してください。');return
        try:
            values=validate(values);self.apply_callback(values);self.values=values
        except (ValueError,StorageError,OSError) as e:
            self.radio_test_status.setText(str(e));return
        self.radio_test_status.setText('接続中…');self._refresh_connection_status()

    def _preview_alert(self):
        self.alert_player.stop();self.alert_player.play(self.alert_volume.value(),self.alert_sound.currentData())

    def done(self,result):
        self.alert_player.stop()
        if getattr(self,'_radio_test_manager',None) is not None:self._finish_radio_test('')
        if getattr(self,'_virtual_op_timer',None) is not None:self._virtual_op_timer.stop()
        super().done(result)

    def save(self):
        values=dict(self.values);values.update({k:cb.isChecked() for k,cb in self.checks.items()});values['backup_keep']=int(self.keep.currentText());values.update(self._radio_values())
        values.update(alert_volume=self.alert_volume.value(),alert_sound=self.alert_sound.currentData())
        if values['radio_enabled'] and not values['radio_model']:
            self.error.setText('無線機接続を使用する場合は無線機を選択してください。');return
        from radio_control import CUSTOM_ICOM,CUSTOM_HAMLIB
        if values['radio_enabled'] and values['radio_model']==CUSTOM_ICOM and not values['radio_civ_address']:
            self.error.setText('その他ICOMではCI-Vアドレスを入力してください。');return
        if values['radio_enabled'] and values['radio_model']==CUSTOM_HAMLIB and not values['radio_hamlib_model']:
            self.error.setText('その他Hamlib対応機ではHamlib Model IDを入力してください。');return
        try:self.apply_callback(validate(values))
        except (ValueError,StorageError,OSError) as e:self.error.setText(str(e));return
        self.accept()

