"""PSLog 1.14 application entry point and main/session UI."""
import sys
import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path
from storage import Repository, StorageError, Snapshot, load_settings, save_settings, VERSION
from preferences import validate as validate_preferences
from PySide6.QtCore import Qt, QTimer, QEvent, Signal
from window_geometry import fitted,fit_widget,state as window_state,areas as window_areas
from PySide6.QtGui import QFont,QIcon,QColor,QPen,QPalette
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QGridLayout,QLabel,QLineEdit,QPushButton,QCheckBox,QComboBox,QGroupBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QDialog,QDialogButtonBox,QInputDialog,QScrollArea,QFileDialog,QSizePolicy,
    QTabBar,QStackedWidget,QMenu,QStylePainter,QStyleOptionTab,QStyle)
from app_paths import data_directory,open_folder
from path_label import PathLabel
from model import QSO, now_jst, default_rst, validate_station, LOCATIONS, preserve_grid
from input_normalization import callsign as normalize_callsign, amateur_callsign_entry, date_text, machine_text, time_text
from mode_text import split_mode_value, combine_mode_value
from remarks_sections import compose as compose_remarks, validate_component as validate_remarks_component
from record_time import needs_confirmation as record_time_needs_confirmation
from band_stats import band_badge,total_badge
from search import session_rows,embedded_history_hit,file_identity,Hit
from free_radio import (FREE_TYPES,radio_values,validate_free_call,validate_model,normalize_free_call,free_path,free_files,free_file_identity,free_models,free_profiles,ensure_free_logbook,FreeQSO)
from free_search import FreeCriteria,free_search
from session_state import (MAX_STANDARD,MAX_EASY,MAX_FREE,MAX_CONTEST,RECENT_LIMIT,restore as restore_workspace_state,
    standard_session,easy_session,free_session,contest_session,next_standard_slot,next_easy_slot,next_free_slot,contest_colors,session_title,serializable,recent_snapshot,reopen_snapshot,
    clean_contest_name,clean_event_ym,contest_suffix)

RESTART_EXIT_CODE=69

FILE_MENU_ITEMS=(
    '本体の場所を開く','ログを再読込',None,
    'ログファイルの場所を開く','出力ファイルの場所を開く','レポートの場所を開く',None,
    'PSLog再起動','PSLog終了',
)

def app_resource(relative):
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    return base/relative

class SingleInstanceGuard:
    """Windows named mutex guard. OS releases it automatically on process exit/crash."""
    NAME=r'Local\PSLog_SingleInstance'
    ERROR_ALREADY_EXISTS=183
    def __init__(self):
        self.handle=None;self.already_running=False
        if sys.platform!='win32':
            return
        kernel32=ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype=wintypes.HANDLE
        kernel32.CloseHandle.argtypes=[wintypes.HANDLE]
        kernel32.CloseHandle.restype=wintypes.BOOL
        handle=kernel32.CreateMutexW(None,False,self.NAME)
        if not handle:
            error=kernel32.GetLastError()
            raise OSError(error,'PSLogの二重起動確認用Mutexを作成できません。')
        if kernel32.GetLastError()==self.ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle);self.already_running=True
        else:
            self.handle=handle
    def release(self):
        if self.handle is not None and sys.platform=='win32':
            ctypes.windll.kernel32.CloseHandle(self.handle);self.handle=None

class SessionTabBar(QTabBar):
    """Tab bar with middle-click close and per-contest visual identity."""
    middleCloseRequested=Signal(int)
    def __init__(self,parent=None):
        super().__init__(parent);self._contest_colors={};self._free_tabs=set()
        self.setMovable(True);self.setExpanding(False);self.setDocumentMode(False)
        self.setUsesScrollButtons(True)
        # Keep the tab title itself unchanged.  Add visual breathing room around
        # the label via the tab style so tabText() remains the real session name.
        self.setStyleSheet('QTabBar::tab { padding: 5px 14px 5px 8px; min-height: 24px; }')
    def set_contest_colors(self,colors):
        self._contest_colors=dict(colors);self.update()
    def set_free_tabs(self,indexes):
        self._free_tabs=set(indexes);self.update()
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            index=self.tabAt(event.position().toPoint())
            if index>=0:
                self.middleCloseRequested.emit(index);event.accept();return
        super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        painter=QStylePainter(self)
        for index in range(self.count()):
            option=QStyleOptionTab();self.initStyleOption(option,index)
            color=self._contest_colors.get(index);selected=index==self.currentIndex();free_tab=index in self._free_tabs
            if not color and not selected:
                painter.drawControl(QStyle.ControlElement.CE_TabBarTab,option);continue
            painter.save()
            # For the selected tab do not ask the native style to paint the tab
            # shape: Windows styles add a bottom edge there.  Paint the face and
            # only the top/left/right edges ourselves so the selected tab opens
            # visually into the page below.
            if not selected:
                painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape,option)
            rect=option.rect.adjusted(2,2,-2,-1)
            if color:
                fill=QColor(color['selected'] if selected else color['light']);edge=QColor(color['dark']);width=2 if selected else 1
            elif free_tab:
                fill=QColor('#CDEFF7');edge=QColor('#67B9CF');width=1
            else:
                fill=QColor('#E3F1E6');edge=QColor('#93BCA0');width=1
            painter.fillRect(rect,fill);painter.setPen(QPen(edge,width))
            if selected:
                painter.drawLine(rect.topLeft(),rect.topRight())
                painter.drawLine(rect.topLeft(),rect.bottomLeft())
                painter.drawLine(rect.topRight(),rect.bottomRight())
            else:
                painter.drawRect(rect.adjusted(0,0,-1,-1))
            text_color=QColor(color['dark']) if color else (QColor('#176B80') if free_tab else QColor('#285B37'))
            option.palette.setColor(QPalette.ColorRole.WindowText,text_color)
            option.palette.setColor(QPalette.ColorRole.ButtonText,text_color)
            option.palette.setColor(QPalette.ColorRole.Text,text_color)
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabLabel,option);painter.restore()

class Window(QMainWindow):
    def __init__(self, data_root=None, reset_window=False):
        super().__init__()
        self._reset_window_on_start=bool(reset_window)
        self.setWindowTitle(f'PSLog Ver{VERSION}')
        self.data_root=data_directory(data_root)
        from logbook_sources import ensure_logbook_directories
        ensure_logbook_directories(self.data_root)
        # Update-only modules are intentionally not imported during ordinary
        # startup.  This keeps normal logging independent from updater health;
        # update_launcher performs its own layout checks only when updating.
        self.repo=Repository(self.data_root); self.sessions={}
        self.asset_sync_warning=''
        try:
            # Official definitions are application-managed assets.  Synchronize
            # them at startup so an updater actually delivers corrected rules,
            # while bundled_sync preserves user-modified/user-defined files.
            from contest_rules import RuleStore
            from cabrillo_templates import TemplateStore
            RuleStore(self.data_root);TemplateStore(self.data_root)
        except (ValueError,OSError,StorageError) as ex:
            self.asset_sync_warning='公式定義データの更新を完了できませんでした: '+str(ex)
        self.config_path=self.data_root/'config'/'conf.cfg'
        self.config_snapshot=Snapshot.read(self.config_path)
        self.settings=validate_preferences(load_settings(self.data_root))
        self.config_snapshot.check(self.config_path)
        self.repo.backup_keep=self.settings['backup_keep']
        self.workspace_sessions,self.active_workspace_index,self.recent_workspace_sessions=restore_workspace_state(self.settings,now_jst())
        self._workspace_loading=False;self._workspace_switching=False;self._country_db=None
        self.resize(1360, 850)
        self.rows = []
        self.station = None
        self.free_station = None
        self._easy_qso_date=''
        self._easy_prepared_call=''
        self.blacklist_ack = None
        self.setStyleSheet('''
            /* overall: a very light blue-gray, while editable fields stay white */
            QMainWindow, QDialog {background:#eef2f5;}
            QWidget {color:#20262b; font-size:14px;}
            QWidget#mainRoot {background:#eef2f5;}
            QScrollArea {background:#eef2f5; border:0;}
            QLineEdit,QComboBox {background:white; border:1px solid #9ba6af; padding:4px 6px; min-height:20px;}
            QLineEdit:focus,QComboBox:focus {border:1px solid #2563a8;}

            /* menu: only a gentle blue cue on hover / selection */
            QMenuBar {background:#e8edf1; color:#20262b;}
            QMenuBar::item {background:transparent; padding:4px 8px;}
            QMenuBar::item:selected {background:#dceaf4; border-radius:3px;}
            QMenuBar::item:pressed {background:#cfe1ee; border-radius:3px;}
            QMenu {background:#f7f9fa; border:1px solid #b8c3cb;}
            QMenu::item {padding:5px 24px 5px 9px;}
            QMenu::item:selected {background:#dceaf4;}
            QMenu::separator {height:1px; background:#d2dbe1; margin:4px 8px;}

            QPushButton {padding:5px 12px; border:1px solid #9ba6af; background:#e8ecf0; min-height:20px;}
            QPushButton:hover {background:#dbe3ea; border-color:#7f8d98;}
            QPushButton:pressed {background:#c8d2db; border-color:#65737f;}
            QPushButton:focus {border:1px solid #2563a8;}
            QPushButton:disabled {background:#eef0f2; color:#9aa2a8; border-color:#c8cdd1;}
            QPushButton#primary {background:#2469b0; color:white; border:1px solid #1d5998;}
            QPushButton#primary:hover {background:#2e79c2; border-color:#1b5f9f;}
            QPushButton#primary:pressed {background:#174f86; border-color:#123f6c;}
            QPushButton#primary:disabled {background:#aebdcc; color:#eef2f5; border-color:#9eabb7;}
            QPushButton#compactBlue {background:#2f6fa7; color:white; border:1px solid #255f91; padding:0 8px; min-height:0px; max-height:21px;}
            QPushButton#compactBlue:hover {background:#3d7fb8; border-color:#245d8c;}
            QPushButton#compactBlue:pressed {background:#245b8a; border-color:#1d4b73;}
            QPushButton#compactBlue:disabled {background:#d8dde2; color:#8b949b; border-color:#c2c8cd;}

            QGroupBox {border:1px solid #bdc8cf; margin-top:8px; padding-top:6px; background:transparent;}
            QGroupBox::title {subcontrol-origin:margin; left:8px; padding:0 3px;}
            QTableWidget {background:#f7faf6; gridline-color:#d6dfd0; border:1px solid #bdcbb4;}
            QHeaderView::section {background:#e1e9dc; padding:5px; border:0; border-bottom:1px solid #bac9b1;}
            QLabel#path {color:#245d98;}
            QLabel#clock {padding:0 8px; background:transparent;}
            QLabel#status {background:#fff2cf; padding:8px; color:#4c4226;}

            /* 4px accent directly below the native menu bar */
            QWidget#menuAccent {
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #6fa37d, stop:0.48 #93bca0, stop:1 #dceadf);
            }
        ''')
        self.menus()
        self.clock=QLabel(); self.clock.setObjectName('clock'); self.clock.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
        self.clock.setMinimumWidth(self.clock.fontMetrics().horizontalAdvance('0000-00-00 00:00:00 JST')+20)
        self.menuBar().setCornerWidget(self.clock,Qt.Corner.TopRightCorner)
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(1000); self.tick()
        central=QWidget(); central_layout=QVBoxLayout(central); central_layout.setContentsMargins(0,0,0,0); central_layout.setSpacing(0)
        accent=QWidget(); accent.setObjectName('menuAccent'); accent.setFixedHeight(3); central_layout.addWidget(accent)

        # Session tabs stay outside the scroll area so they never disappear when
        # a smaller display needs vertical scrolling.  The + button is an action,
        # not a dummy page.
        tabrow=QWidget(); tr=QHBoxLayout(tabrow); tr.setContentsMargins(8,4,8,2); tr.setSpacing(4)
        self.session_tabs=SessionTabBar();tr.addWidget(self.session_tabs,1)
        self.add_session_button=QPushButton('＋タブ');self.add_session_button.setObjectName('primary');self.add_session_button.setToolTip('タブを追加・再開')
        self.add_session_button.setFixedWidth(76);tr.addWidget(self.add_session_button,0,Qt.AlignmentFlag.AlignTop)
        central_layout.addWidget(tabrow)
        self.page_stack=QStackedWidget();central_layout.addWidget(self.page_stack,1);self.setCentralWidget(central)

        # Standard page: this is the existing PSLog main UI, kept intentionally
        # close to Ver1.01/early 1.02 behavior.
        root=QWidget(); root.setObjectName('mainRoot')
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(root); self.standard_scroll=scroll;self.page_stack.addWidget(scroll)
        outer = QVBoxLayout(root); outer.setContentsMargins(8,6,8,6); outer.setSpacing(6)
        stationbox=QGroupBox('自局・ログファイル'); self.standard_stationbox=stationbox; sl=QGridLayout(stationbox); sl.setContentsMargins(8,8,8,8); sl.setHorizontalSpacing(8); sl.setVerticalSpacing(4)
        self.own=QLineEdit(self.settings.get('own','')); self.suffix=QLineEdit(self.settings.get('suffix','')); self.suffix.setPlaceholderText('任意：JP1220 など')
        sl.addWidget(QLabel('自局コールサイン（/ 含む）'),0,0); sl.addWidget(QLabel('ログファイル付与文字'),0,1,1,2)
        path_head=QWidget();path_head_row=QHBoxLayout(path_head);path_head_row.setContentsMargins(0,0,0,0);path_head_row.setSpacing(6);path_head_row.addWidget(QLabel('現在のログファイル'));path_head_row.addStretch()
        self.show_current_log_button=QPushButton('全件表示');self.show_current_log_button.setObjectName('compactBlue');self.show_current_log_button.setFixedHeight(21);self.show_current_log_button.setToolTip('現在の自局コールとログファイルを「ログ検索・編集」へ渡し、全件を表示します。');self.show_current_log_button.clicked.connect(lambda:self.open_current_log_search(False));path_head_row.addWidget(self.show_current_log_button,0,Qt.AlignmentFlag.AlignVCenter);sl.addWidget(path_head,0,3)
        sl.addWidget(self.own,1,0); sl.addWidget(self.suffix,1,1)
        setbutton=self.button('SET',self.set_station,True); sl.addWidget(setbutton,1,2)
        self.path=PathLabel('自局コールサインをSETしてください'); self.path.setObjectName('path'); self.path.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter); sl.addWidget(self.path,1,3)
        sl.setColumnStretch(0,3); sl.setColumnStretch(1,3); sl.setColumnStretch(2,0); sl.setColumnStretch(3,6)
        outer.addWidget(stationbox)
        split=QHBoxLayout(); outer.addLayout(split,1)
        self.entry=QGroupBox('交信入力'); split.addWidget(self.entry,5); form=QVBoxLayout(self.entry)
        self.call_label=QLabel('相手コールサイン');self.call_label.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        call_label_font=self.call_label.font();call_label_font.setBold(True);self.call_label.setFont(call_label_font);form.addWidget(self.call_label)
        callrow=QHBoxLayout(); self.call=QLineEdit(); self.call.setPlaceholderText('JX1XXX')
        call_font=self.call.font();call_font.setBold(True);self.call.setFont(call_font);callrow.addWidget(self.call)
        callrow.addWidget(self.button('RETURN',self.start_qso,True)); form.addLayout(callrow)
        self.call.returnPressed.connect(self.start_qso)
        self.call.textEdited.connect(lambda text:self._filter_amateur_callsign_editor(self.call,text))
        self.call.textChanged.connect(lambda: setattr(self,'blacklist_ack',None))
        grid=QGridLayout(); self.fields={}
        for column in range(4):grid.setColumnStretch(column,1)
        for key,label,row,col,span in [('date','Date',0,0,2),('time','Time · JST',0,2,2),
            ('band','Band · MHz',2,0,2),('mode','Mode',2,2,2),
            ('sent','His RST（送信）',4,0,2),('received','My RST（受信）',4,2,2),
            ('his_qth','His QTH',6,0,3),('code','JCC / JCG',6,3,1),
            ('my_qth','My QTH',8,0,4),('remarks','RMKS',10,0,4)]:
            e=QComboBox() if key in ('band','mode') else QLineEdit()
            if isinstance(e,QComboBox):
                e.setEditable(True); e.addItems(['0.135','0.475','1.8','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000'] if key=='band' else ['SSB','FM','AM','CW','RTTY','FT8','FT4','FT2','SSTV','FreeDV']); e.setCurrentText('7' if key=='band' else 'FT8')
            self.fields[key]=e
            if key=='mode':
                mode_label=QWidget(); mode_label_row=QHBoxLayout(mode_label); mode_label_row.setContentsMargins(0,0,0,0); mode_label_row.setSpacing(8)
                mode_label_row.addWidget(QLabel(label))
                self.sub_mode_on=QCheckBox('Sub'); mode_label_row.addWidget(self.sub_mode_on); mode_label_row.addStretch()
                grid.addWidget(mode_label,row,col,1,span)

                mode_editor=QWidget(); self.mode_editor_layout=QHBoxLayout(mode_editor); self.mode_editor_layout.setContentsMargins(0,0,0,0); self.mode_editor_layout.setSpacing(6)
                self.mode_editor_layout.addWidget(e,55)
                self.sub_mode=QComboBox(); self.sub_mode.setEditable(True); self.sub_mode.setPlaceholderText('Sub')
                self.mode_editor_layout.addWidget(self.sub_mode,45); self.sub_mode.hide()
                grid.addWidget(mode_editor,row+1,col,1,span)
                self.sub_mode_on.toggled.connect(self.toggle_sub_mode)
            else:
                if key=='remarks':
                    remarks_label=QWidget();remarks_label_row=QHBoxLayout(remarks_label);remarks_label_row.setContentsMargins(0,0,0,0);remarks_label_row.setSpacing(8)
                    remarks_label_row.addWidget(QLabel(label));self.rmks2_toggle=QCheckBox('RMKS2を表示');remarks_label_row.addWidget(self.rmks2_toggle);remarks_label_row.addStretch()
                    grid.addWidget(remarks_label,row,col,1,span)
                else:
                    grid.addWidget(QLabel(label),row,col,1,span)
                grid.addWidget(e,row+1,col,1,span)
        self.rmks2_label=QLabel('RMKS2');self.rmks2=QLineEdit();self.rmks2.setPlaceholderText('任意：追加メモ')
        grid.addWidget(self.rmks2_label,12,0,1,4);grid.addWidget(self.rmks2,13,0,1,4)
        self.rmks2_label.hide();self.rmks2.hide();self.rmks2_toggle.toggled.connect(self.rmks2_visibility_changed)
        form.addLayout(grid)
        self.fields['my_qth'].setText(self.settings.get('my_qth',''))
        for key in ('band','mode'):self.set_text(key,self.settings.get(key,self.text(key)))
        self.fields['his_qth'].setPlaceholderText('GL・所在地を自由入力')
        self.fields['remarks'].setPlaceholderText('BURO  hQSL.R  コンテストナンバー・メモなど')
        helper=QHBoxLayout(); self.location_on=QCheckBox('所在地補助'); self.location_on.setChecked(True)
        helper.addWidget(self.location_on); self.location_button=self.button('HIS QTH所在地',lambda:self.location('his_qth'))
        helper.addWidget(self.location_button);self.my_location_button=self.button('MY QTH所在地',lambda:self.location('my_qth'));helper.addWidget(self.my_location_button);helper.addStretch();form.addLayout(helper)
        self.location_on.setChecked(self.settings['location_assist'])
        self.location_on.toggled.connect(lambda on:(self.location_button.setEnabled(on),self.my_location_button.setEnabled(on)))
        self.location_button.setEnabled(self.location_on.isChecked());self.my_location_button.setEnabled(self.location_on.isChecked())
        from location_suggest import LocationSuggestor
        self.his_qth_suggest=LocationSuggestor(self.data_root,self.fields['his_qth'],self.fields['code'])
        self.his_qth_suggest.set_enabled(self.location_on.isChecked())
        self.location_on.toggled.connect(self.his_qth_suggest.set_enabled)
        # Keep the input rows compact like the contest entry panel.  Any spare
        # height belongs between the location helper row and the keep-options,
        # not inside the callsign label at the top.
        form.addStretch(1)
        keep=QHBoxLayout(); self.keep_band=QCheckBox('バンドを維持'); self.keep_mode=QCheckBox('モードを維持'); self.auto_rst=QCheckBox('モードに応じてRSTを補助')
        for key,cb in [('keep_band',self.keep_band),('keep_mode',self.keep_mode),('auto_rst',self.auto_rst)]:cb.setChecked(self.settings.get(key,True));keep.addWidget(cb)
        form.addLayout(keep)
        form.addWidget(self.button('REC / RETURN　記録',self.record,True))
        self.fields['mode'].currentTextChanged.connect(lambda _text:self.mode_changed(self.text('mode')))
        self.sub_mode.currentTextChanged.connect(lambda _text:self.mode_changed(self.text('mode')))
        self.order=list(self.fields)
        for i,key in enumerate(self.order):
            e=self.fields[key]; le=e.lineEdit() if isinstance(e,QComboBox) else e
            if key=='mode':
                le.returnPressed.connect(self.mode_return_pressed)
            else:
                le.returnPressed.connect(self.remarks_return_pressed if key=='remarks' else lambda i=i:self.fields[self.order[i+1]].setFocus())
        self.sub_mode.lineEdit().returnPressed.connect(lambda:self.fields['sent'].setFocus())
        self.rmks2.returnPressed.connect(self.record)
        for key in ('date','time','sent','received','code'):
            self.fields[key].editingFinished.connect(lambda key=key:self._normalize_standard_field(key))
        for key in ('band','mode'):
            self.fields[key].lineEdit().editingFinished.connect(lambda key=key:self._normalize_standard_field(key))
        self.sub_mode.lineEdit().editingFinished.connect(lambda:self._normalize_sub_mode())
        self.fields['date'].textChanged.connect(lambda: self.update_path() if self.station else None)
        self.entry.setEnabled(False)
        history=QGroupBox('LogSearch'); self.standard_history=history; split.addWidget(history,6); hl=QVBoxLayout(history)
        self.limited=QCheckBox('検索範囲を選択中のログに限定'); hl.addWidget(self.limited)
        self.limited.toggled.connect(self.search)
        self.summary=QLabel('相手コールサインを入力してRETURN'); hl.addWidget(self.summary)
        self.table=QTableWidget(0,8); self.table.setHorizontalHeaderLabels(['相手コール','日時 JST','Band','Mode','送 / 受','QTH','JCC/JCG','QSL'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True); hl.addWidget(self.table)
        self.table.doubleClicked.connect(lambda index:self.show_standard_history_detail(index.row()))
        self._standard_history_visible=[]
        self.more=QLabel('実ログを読み込みます'); hl.addWidget(self.more)
        self.status=QLabel('記録はTXTへ保存します。所在地の未確認表記は候補を確認して選択してください。'+(('\n'+self.asset_sync_warning) if self.asset_sync_warning else '')); self.status.setObjectName('status'); self.status.setWordWrap(True); hl.addWidget(self.status)

        # Do not let a very small screen crush the standard form until every
        # control technically fits.  The main QScrollArea is the safety net:
        # below this content height it must scroll instead.  560px still fits
        # comfortably in the normal 700/768px-class layouts after the fixed
        # menu/tab rows are accounted for.
        root.setMinimumHeight(560)

        # EASY page: the same PSLog log/repository underneath, but a deliberately
        # simplified two-step entry flow.  Only the left entry pane changes page;
        # LogSearch remains visible on the right.
        self.easy_scroll=self._build_easy_page();self.page_stack.addWidget(self.easy_scroll)

        # Free-radio page is shared by all free-radio tabs.
        self.free_scroll=self._build_free_page();self.page_stack.addWidget(self.free_scroll)

        # Contest page is a separate compact workspace, shared by all contest tabs.
        self.contest_scroll=self._build_contest_page();self.page_stack.addWidget(self.contest_scroll)

        self.session_tabs.currentChanged.connect(self._on_workspace_changed)
        self.session_tabs.tabCloseRequested.connect(self._close_workspace)
        self.session_tabs.middleCloseRequested.connect(self._close_workspace)
        self.session_tabs.tabMoved.connect(self._workspace_moved)
        self.add_session_button.clicked.connect(self._show_add_session_menu)
        self._rebuild_session_tabs()
        self._load_workspace(self.active_workspace_index,initial=True)
        if self._active_workspace().get('type') in ('standard','easy') and not self._active_own_text().strip():QTimer.singleShot(0,self.first_start)
        self._geometry_ready=False;self._was_maximized=False
        app=QApplication.instance()
        app.screenAdded.connect(self.screen_environment_changed)
        app.screenRemoved.connect(self.screen_environment_changed)
        self._watched_screens=[]
        self.watch_screens()

    def watch_screens(self):
        for screen in QApplication.screens():
            if screen not in self._watched_screens:
                screen.availableGeometryChanged.connect(self.screen_environment_changed)
                screen.logicalDotsPerInchChanged.connect(self.screen_environment_changed)
                self._watched_screens.append(screen)
    def screen_environment_changed(self,*args):
        self.watch_screens()
        if self.isVisible() and not getattr(self,'_correcting_window',False):QTimer.singleShot(0,self.correct_window)
    def correct_window(self):
        if not self.isVisible() or self.isMinimized() or getattr(self,'_correcting_window',False):return
        self._correcting_window=True
        try:
            maximized=self.isMaximized()
            saved=window_state(self)
            if maximized:self.showNormal()
            fit_widget(self,saved)
            if maximized:self.showMaximized()
        finally:self._correcting_window=False
    def showEvent(self,event):
        super().showEvent(event)
        QTimer.singleShot(0,self.apply_native_titlebar)
        if not getattr(self,'_geometry_ready',False):
            self._geometry_ready=True
            QTimer.singleShot(0,self.restore_window)
    def restore_window(self):
        if not self.isVisible():return
        saved={} if self._reset_window_on_start else self.settings.get('window_geometry',{})
        fit_widget(self,saved)
        if not self._reset_window_on_start and isinstance(saved,dict) and saved.get('maximized') is True:self.showMaximized()
        if self.windowHandle():self.windowHandle().screenChanged.connect(self.screen_environment_changed)
    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type()==QEvent.Type.WindowStateChange and not self.isMinimized():
            self._was_maximized=self.isMaximized()
            if getattr(self,'_geometry_ready',False) and not self.isMaximized() and not getattr(self,'_correcting_window',False):QTimer.singleShot(0,self.correct_window)

    @staticmethod
    def _colorref(value):
        value=value.lstrip('#')
        r,g,b=(int(value[i:i+2],16) for i in (0,2,4))
        return r | (g<<8) | (b<<16)

    def apply_native_titlebar(self):
        if sys.platform!='win32':
            return
        try:
            hwnd=int(self.winId())
            dwm=ctypes.windll.dwmapi
            # Windows 11 DWM attributes.  On systems that do not support them,
            # DwmSetWindowAttribute simply fails and the native title bar remains.
            for attr,color in ((35,'#6fa37d'),(36,'#1f2a24')):
                value=ctypes.c_uint(self._colorref(color))
                dwm.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd), ctypes.c_uint(attr),
                    ctypes.byref(value), ctypes.sizeof(value)
                )
        except Exception:
            pass

    def _build_easy_page(self):
        root=QWidget();root.setObjectName('mainRoot')
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(8,6,8,6);outer.setSpacing(6)

        station=QGroupBox('自局・ログファイル');self.easy_stationbox=station
        grid=QGridLayout(station);grid.setContentsMargins(8,8,8,8);grid.setHorizontalSpacing(8);grid.setVerticalSpacing(4)
        grid.addWidget(QLabel('自局コールサイン（/ 含む）'),0,0)
        path_head=QWidget();path_head_row=QHBoxLayout(path_head);path_head_row.setContentsMargins(0,0,0,0);path_head_row.setSpacing(6)
        path_head_row.addWidget(QLabel('現在のログファイル'));path_head_row.addStretch()
        self.e_show_current_log_button=QPushButton('全件表示');self.e_show_current_log_button.setObjectName('compactBlue');self.e_show_current_log_button.setFixedHeight(21)
        self.e_show_current_log_button.setToolTip('現在の自局コールとログファイルを「ログ検索・編集」へ渡し、全件を表示します。')
        self.e_show_current_log_button.clicked.connect(lambda:self.open_current_log_search(False));path_head_row.addWidget(self.e_show_current_log_button,0,Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(path_head,0,2,1,2)
        self.e_own=QLineEdit();own_font=self.e_own.font();own_font.setBold(True);self.e_own.setFont(own_font)
        grid.addWidget(self.e_own,1,0);grid.addWidget(self.button('SET',self.easy_set_station,True),1,1)
        self.e_path=PathLabel('自局コールサインをSETしてください');self.e_path.setObjectName('path');self.e_path.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.e_path,1,2,1,2);grid.setColumnStretch(0,4);grid.setColumnStretch(1,0);grid.setColumnStretch(2,3);grid.setColumnStretch(3,3)
        outer.addWidget(station)

        split=QHBoxLayout();outer.addLayout(split,1)
        self.easy_entry=QGroupBox('EASY入力');self.easy_entry.setObjectName('easyEntryBox')
        self.easy_entry.setStyleSheet('QGroupBox#easyEntryBox {border:1px solid #6fa37d; margin-top:8px; padding-top:6px; background:transparent;} QGroupBox#easyEntryBox::title {subcontrol-origin:margin; left:8px; padding:0 3px;}')
        split.addWidget(self.easy_entry,5)
        easy_layout=QVBoxLayout(self.easy_entry);easy_layout.setContentsMargins(10,10,10,10);easy_layout.setSpacing(8)
        self.e_pages=QStackedWidget();easy_layout.addWidget(self.e_pages,1)

        # Page 1: the information normally exchanged while the QSO is in progress.
        p1=QWidget();p1v=QVBoxLayout(p1);p1v.setContentsMargins(4,2,4,2);p1v.setSpacing(9)
        p1_head=QLabel('1 / 2 ページ');p1_head.setAlignment(Qt.AlignmentFlag.AlignCenter);p1_head.setStyleSheet('font-size:17px; font-weight:600;')
        p1v.addWidget(p1_head)
        bm=QGridLayout();bm.setHorizontalSpacing(12);bm.setVerticalSpacing(5)
        band_label=QLabel('バンド（MHz）');mode_label=QLabel('モード');band_label.setStyleSheet('font-size:16px; font-weight:600;');mode_label.setStyleSheet('font-size:16px; font-weight:600;')
        bm.addWidget(band_label,0,0);bm.addWidget(mode_label,0,1)
        self.e_band=QComboBox();self.e_band.setEditable(True);self.e_band.addItems(['0.135','0.475','1.8','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000'])
        mode_host=QWidget();mode_row=QHBoxLayout(mode_host);mode_row.setContentsMargins(0,0,0,0);mode_row.setSpacing(6)
        self.e_mode=QComboBox();self.e_mode.setEditable(True);self.e_mode.addItems(['SSB','FM','AM','CW','RTTY','FT8','FT4','FT2','SSTV','FreeDV'])
        self.e_sub_on=QCheckBox('Sub');self.e_sub=QComboBox();self.e_sub.setEditable(True);self.e_sub.setPlaceholderText('Sub');self.e_sub.hide()
        mode_row.addWidget(self.e_mode,55);mode_row.addWidget(self.e_sub_on,0);mode_row.addWidget(self.e_sub,45)
        self.e_band.setStyleSheet('font-size:17px; min-height:30px;');self.e_mode.setStyleSheet('font-size:17px; min-height:30px;');self.e_sub.setStyleSheet('font-size:17px; min-height:30px;')
        bm.addWidget(self.e_band,1,0);bm.addWidget(mode_host,1,1);bm.setColumnStretch(0,1);bm.setColumnStretch(1,1);p1v.addLayout(bm)

        e_call_label=QLabel('相手のコールサイン');e_call_label.setStyleSheet('font-size:19px; font-weight:700; margin-top:8px;')
        self.e_call=QLineEdit();self.e_call.setPlaceholderText('JX1XXX');self.e_call.setStyleSheet('font-size:24px; font-weight:700; min-height:42px; padding:6px 8px;')
        p1v.addWidget(e_call_label);p1v.addWidget(self.e_call)
        rst=QGridLayout();rst.setHorizontalSpacing(12);rst.setVerticalSpacing(4)
        sent_label=QLabel('送信RST');recv_label=QLabel('受信RST');sent_label.setStyleSheet('font-size:16px;');recv_label.setStyleSheet('font-size:16px;')
        self.e_sent=QLineEdit();self.e_received=QLineEdit();self.e_sent.setStyleSheet('font-size:18px; min-height:30px;');self.e_received.setStyleSheet('font-size:18px; min-height:30px;')
        rst.addWidget(sent_label,0,0);rst.addWidget(recv_label,0,1);rst.addWidget(self.e_sent,1,0);rst.addWidget(self.e_received,1,1);rst.setColumnStretch(0,1);rst.setColumnStretch(1,1);p1v.addLayout(rst)
        p1v.addStretch(1)
        self.e_next=QPushButton('次へ');self.e_next.setObjectName('primary');self.e_next.setStyleSheet('font-size:19px; font-weight:700; min-height:42px;');p1v.addWidget(self.e_next)
        self.e_pages.addWidget(p1)

        # Page 2: location, memo and finally time/record.  Time belongs here on
        # purpose: EASY assumes the operator may need time to type the details.
        p2=QWidget();p2v=QVBoxLayout(p2);p2v.setContentsMargins(4,2,4,2);p2v.setSpacing(8)
        p2top=QHBoxLayout();self.e_back=QPushButton('最初に戻る');self.e_back.setStyleSheet('font-size:15px; min-height:28px;');p2top.addWidget(self.e_back);p2top.addStretch()
        p2_head=QLabel('2 / 2 ページ');p2_head.setStyleSheet('font-size:17px; font-weight:600;');p2top.addWidget(p2_head);p2top.addStretch();p2v.addLayout(p2top)
        summary_box=QGroupBox('1 / 2 ページの入力内容');summary_box.setMinimumHeight(132);sv=QVBoxLayout(summary_box)
        self.e_page1_summary=QLabel();self.e_page1_summary.setWordWrap(True);self.e_page1_summary.setStyleSheet('font-size:15px; line-height:1.25;');sv.addWidget(self.e_page1_summary);p2v.addWidget(summary_box)

        hq=QGroupBox('His QTH（相手の運用場所）');hqg=QGridLayout(hq);hqg.setHorizontalSpacing(8);hqg.setVerticalSpacing(5)
        hqg.addWidget(QLabel('JCC/JCG'),0,0);self.e_code=QLineEdit();self.e_code.setStyleSheet('font-size:16px; min-height:28px;');hqg.addWidget(self.e_code,0,1)
        self.e_code_to_qth=QPushButton('JCC/JCGから名称を入れる');self.e_code_to_qth.setStyleSheet('font-size:15px; min-height:28px;');hqg.addWidget(self.e_code_to_qth,0,2)
        hqg.addWidget(QLabel('名称'),1,0);self.e_his_qth=QLineEdit();self.e_his_qth.setPlaceholderText('相手の運用場所');self.e_his_qth.setStyleSheet('font-size:16px; min-height:28px;');hqg.addWidget(self.e_his_qth,1,1,1,2);hqg.setColumnStretch(1,1);p2v.addWidget(hq)
        mq=QGroupBox('My QTH（自分の運用場所）');mqg=QGridLayout(mq);mqg.addWidget(QLabel('名称'),0,0);self.e_my_qth=QLineEdit();self.e_my_qth.setPlaceholderText('自分の運用場所');self.e_my_qth.setStyleSheet('font-size:16px; min-height:28px;');mqg.addWidget(self.e_my_qth,0,1);mqg.setColumnStretch(1,1);p2v.addWidget(mq)
        rm=QGridLayout();rm.addWidget(QLabel('RMKS（メモ）'),0,0);self.e_remarks=QLineEdit();self.e_remarks.setPlaceholderText('QSL・メモなど');self.e_remarks.setStyleSheet('font-size:16px; min-height:28px;');rm.addWidget(self.e_remarks,1,0);p2v.addLayout(rm)
        time_row=QHBoxLayout();self.e_date_label=QLabel('日付：----/--/--');self.e_date_label.setStyleSheet('font-size:15px;');time_row.addWidget(self.e_date_label);time_row.addStretch();time_row.addWidget(QLabel('時刻（JST）'))
        self.e_time=QLineEdit();self.e_time.setFixedWidth(105);self.e_time.setStyleSheet('font-size:17px; min-height:28px;');time_row.addWidget(self.e_time);p2v.addLayout(time_row)
        self.e_record=QPushButton('登録');self.e_record.setObjectName('primary');self.e_record.setStyleSheet('font-size:20px; font-weight:700; min-height:44px;');p2v.addWidget(self.e_record)
        self.e_pages.addWidget(p2)

        # LogSearch intentionally remains beside both EASY pages.
        history=QGroupBox('LogSearch');self.easy_history=history;split.addWidget(history,6);hl=QVBoxLayout(history)
        history.setStyleSheet('QGroupBox { font-size:16px; } QCheckBox,QLabel,QTableWidget { font-size:15px; } QHeaderView::section { font-size:15px; }')
        self.e_limited=QCheckBox('検索範囲を選択中のログに限定');hl.addWidget(self.e_limited)
        self.e_summary=QLabel('相手コールサインを入力して「次へ」');hl.addWidget(self.e_summary)
        self.e_table=QTableWidget(0,8);self.e_table.setHorizontalHeaderLabels(['相手コール','日時 JST','Band','Mode','送 / 受','QTH','JCC/JCG','QSL'])
        self.e_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.e_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.e_table.verticalHeader().setVisible(False)
        self.e_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.e_table.horizontalHeader().setStretchLastSection(True);hl.addWidget(self.e_table)
        self.e_more=QLabel('実ログを読み込みます');hl.addWidget(self.e_more)
        self.e_status=QLabel('EASY入力は2画面で交信を記録します。');self.e_status.setObjectName('status');self.e_status.setWordWrap(True);hl.addWidget(self.e_status)
        self._easy_history_visible=[]

        self.e_sub_on.toggled.connect(self.easy_toggle_sub_mode)
        self.e_mode.currentTextChanged.connect(lambda _text:self.easy_mode_changed())
        self.e_sub.currentTextChanged.connect(lambda _text:self.easy_mode_changed())
        self.e_call.textEdited.connect(lambda text:self._filter_amateur_callsign_editor(self.e_call,text));self.e_call.textChanged.connect(lambda:setattr(self,'blacklist_ack',None))
        self.e_call.returnPressed.connect(self.easy_next_page);self.e_next.clicked.connect(self.easy_next_page);self.e_back.clicked.connect(self.easy_back_page)
        self.e_code_to_qth.clicked.connect(self.easy_apply_qth_from_code);self.e_record.clicked.connect(self.easy_record)
        self.e_limited.toggled.connect(self.easy_search);self.e_table.doubleClicked.connect(lambda index:self.show_easy_history_detail(index.row()))
        self.e_time.editingFinished.connect(self.easy_normalize_time);self.e_code.editingFinished.connect(self.easy_normalize_code)
        root.setMinimumHeight(570)
        return scroll

    def easy_mode_value(self):
        return combine_mode_value(self.e_mode.currentText(),self.e_sub.currentText(),self.e_sub_on.isChecked())

    def easy_set_mode(self,value):
        main_mode,sub=split_mode_value(value)
        self.e_mode.setCurrentText(main_mode);self.e_sub.setCurrentText(sub);self.e_sub_on.setChecked(bool(sub));self.easy_toggle_sub_mode(bool(sub))

    def easy_toggle_sub_mode(self,on):
        self.e_sub.setVisible(bool(on));self.easy_mode_changed()

    def easy_mode_changed(self):
        value=default_rst(self.easy_mode_value()) or ''
        self.e_sent.setText(value);self.e_received.setText(value)
        if not self._workspace_loading and self._active_workspace().get('type')=='easy':
            self._active_workspace()['mode']=self.easy_mode_value()

    def easy_set_station(self):
        return self._activate_easy_station(True)

    def _activate_easy_station(self,save_now):
        try:call=validate_station(self.e_own.text(),'')
        except ValueError as e:QMessageBox.warning(self,'自局設定',str(e));return False
        self.station=(call,'');self.e_own.setText(call);self.easy_entry.setEnabled(True)
        session=self._active_workspace();session.update(call=call,suffix='',band=self.e_band.currentText().strip(),mode=self.easy_mode_value(),my_qth=self.e_my_qth.text())
        self.session_tabs.setTabText(self.active_workspace_index,session_title(session))
        if save_now:
            try:self.persist_settings()
            except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'自局設定の保存',str(e))
        self.reload_easy_logs();self.e_call.setFocus();return True

    def easy_update_path(self):
        try:
            date=self._easy_qso_date or now_jst().strftime('%Y-%m-%d');p=self.repo.path_for(*self.station,date)
            if p not in self.sessions:self.sessions[p]=self.repo.open(p)
            self.e_path.setText(str(p))
        except (ValueError,StorageError,OSError):self.e_path.setText('日付を正しく入力してください')
        self._update_current_log_buttons()

    def reload_easy_logs(self):
        if not self.station:return
        try:
            self.repo.recover();sessions={p:self.repo.open(p) for p in self.repo.files(self.station[0])};self.sessions=sessions;self.rows=session_rows(sessions,self.station[0])
            issues=sum(len(s.log.issues) for s in sessions.values());self.e_status.setText(f'{len(self.rows)}交信を読み込みました。要確認行 {issues}件。')
            if issues:QMessageBox.warning(self,'ログの確認','解釈できない行のあるファイルは保存できません。audit.pyで行番号と理由を確認できます。')
            self.easy_update_path();self.easy_search()
        except (StorageError,OSError) as e:QMessageBox.warning(self,'読み込み',str(e))

    def easy_search(self):
        if not self.station:return
        call=self.e_call.text().strip().upper();base=call.split('/',1)[0] if call else ''
        def same_history_station(value):
            value=(value or '').strip().upper();return bool(base) and (value==base or value.startswith(base+'/'))
        candidates=[(owner,r) for owner,r in self.rows if same_history_station(r.call) and owner[0]==self.station[0] and (not self.e_limited.isChecked() or owner==self.station)]
        if self.e_limited.isChecked():
            year=(self._easy_qso_date[:4] if self._easy_qso_date else str(now_jst().year));candidates=[item for item in candidates if item[1].date[:4]==year]
        candidates.sort(key=lambda item:(item[1].date,item[1].time),reverse=True);visible=candidates[:20];self._easy_history_visible=visible;self.e_table.setRowCount(len(visible))
        for i,(_owner,r) in enumerate(visible):
            values=[r.call,r.date+' '+r.time,r.band,r.mode,r.sent+' / '+r.received,r.his_qth,r.code,'QSLR' if r.confirmed else '—']
            for j,v in enumerate(values):self.e_table.setItem(i,j,QTableWidgetItem(v))
        self.e_summary.setText(self._history_summary_html(base,len(candidates)) if call else '相手コールサインを入力して「次へ」')
        self.e_more.setText('他 '+str(len(candidates)-len(visible))+'件' if len(candidates)>len(visible) else '読み込んだTXTの交信を表示しています')

    def show_easy_history_detail(self,row=None):
        if row is None:row=self.e_table.currentRow()
        self._show_embedded_history_detail(row,getattr(self,'_easy_history_visible',[]),self.reload_easy_logs)

    def easy_next_page(self):
        call=normalize_callsign(self.e_call.text())
        now=now_jst()
        try:
            q=QSO(now.strftime('%Y-%m-%d'),now.strftime('%H:%M'),self.e_band.currentText().strip(),self.easy_mode_value(),call,
                self.e_sent.text().strip(),self.e_received.text().strip(),'','','','');q.validate()
        except ValueError as e:
            QMessageBox.warning(self,'入力確認',str(e));self.e_call.setFocus();return
        self.e_call.setText(q.call);self.e_band.setCurrentText(q.band);self.easy_set_mode(q.mode);self.e_sent.setText(q.sent);self.e_received.setText(q.received)
        self.warn_blacklist(q.call);self.easy_search()
        new_station=q.call!=self._easy_prepared_call
        if new_station:
            self._easy_prepared_call=q.call;self._easy_qso_date=now.strftime('%Y-%m-%d');self.e_time.setText(now.strftime('%H:%M'))
            self.e_his_qth.clear();self.e_code.clear();self.e_remarks.clear()
            try:
                hint=self._country_hint(q.call)
                if hint:self.e_his_qth.setText(hint['country'])
            except (StorageError,OSError):pass
        elif not self._easy_qso_date:
            self._easy_qso_date=now.strftime('%Y-%m-%d');self.e_time.setText(now.strftime('%H:%M'))
        self.e_date_label.setText('日付：'+self._easy_qso_date)
        self.e_page1_summary.setText(f'相手：{q.call}\nバンド：{q.band} MHz　　モード：{q.mode}\nRST：送信 {q.sent or "—"} ／ 受信 {q.received or "—"}')
        self.easy_update_path();self.e_pages.setCurrentIndex(1);self.e_code.setFocus()

    def easy_back_page(self):
        self.e_pages.setCurrentIndex(0);self.e_call.setFocus()

    def easy_apply_qth_from_code(self):
        try:
            from jccjcg_batch import qth_from_code
            qth=qth_from_code(self.data_root,self.e_code.text())
        except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'JCC/JCG',str(e));return
        self.e_his_qth.setText(qth)

    def easy_normalize_time(self):
        try:self.e_time.setText(time_text(self.e_time.text()))
        except ValueError:pass

    def easy_normalize_code(self):
        try:
            from input_normalization import jccjcg_code
            self.e_code.setText(jccjcg_code(self.e_code.text()))
        except ValueError:pass

    def _easy_time_choice(self,qso):
        now=now_jst()
        if not record_time_needs_confirmation(qso.date,qso.time,now,5):return 'normal'
        dialog=QDialog(self);dialog.setWindowTitle('EASY入力：記録時刻の確認');layout=QVBoxLayout(dialog)
        label=QLabel('入力された時刻と現在時刻が5分以上違います。\nどの時刻で登録しますか？');label.setWordWrap(True);layout.addWidget(label)
        row=QHBoxLayout();cancel=QPushButton('キャンセル');current=QPushButton('現時刻で登録');entered=QPushButton('入力された時刻で登録');choice={'value':'cancel'}
        def finish(value):choice['value']=value;dialog.accept()
        cancel.clicked.connect(lambda:finish('cancel'));current.clicked.connect(lambda:finish('current'));entered.clicked.connect(lambda:finish('keep'))
        row.addWidget(cancel);row.addWidget(current);row.addWidget(entered);layout.addLayout(row);dialog.exec()
        if choice['value']=='current':
            now=now_jst();qso.date=now.strftime('%Y-%m-%d');qso.time=now.strftime('%H:%M')
        return choice['value']

    def _easy_confirm_record(self,qso):
        dialog=QDialog(self);dialog.setWindowTitle('EASY入力：登録確認');layout=QVBoxLayout(dialog)
        label=QLabel(f'{qso.date} {qso.time} JST\n{qso.call}　{qso.band} MHz　{qso.mode}\nRST {qso.sent or "—"} / {qso.received or "—"}\n\nこの内容で登録しますか？');label.setWordWrap(True);label.setStyleSheet('font-size:15px;');layout.addWidget(label)
        row=QHBoxLayout();row.addStretch();cancel=QPushButton('キャンセル');save=QPushButton('登録');save.setObjectName('primary');row.addWidget(cancel);row.addWidget(save);layout.addLayout(row)
        result={'ok':False};cancel.clicked.connect(dialog.reject);save.clicked.connect(lambda:(result.__setitem__('ok',True),dialog.accept()));dialog.exec();return result['ok']

    def easy_record(self):
        if self.e_pages.currentIndex()!=1:return
        date=self._easy_qso_date or now_jst().strftime('%Y-%m-%d')
        try:
            validate_remarks_component(self.e_remarks.text(),'RMKS')
            q=QSO(date,self.e_time.text().strip(),self.e_band.currentText().strip(),self.easy_mode_value(),normalize_callsign(self.e_call.text()),
                self.e_sent.text().strip(),self.e_received.text().strip(),self.e_his_qth.text(),self.e_my_qth.text(),self.e_remarks.text(),self.e_code.text());q.validate()
        except ValueError as e:
            QMessageBox.warning(self,'入力確認',str(e));return
        time_choice=self._easy_time_choice(q)
        if time_choice=='cancel':self.e_status.setText('記録を中止しました。時刻を確認してください。');self.e_time.setFocus();self.e_time.selectAll();return
        if time_choice=='normal' and not self._easy_confirm_record(q):return
        try:
            if not self.station:raise StorageError('自局をSETしてください。')
            path=self.repo.path_for(*self.station,q.date);session=self.sessions.get(path) or self.repo.open(path);session.append(q);self.sessions[path]=session
        except (StorageError,OSError) as e:QMessageBox.warning(self,'保存できません',str(e));return
        self.rows=session_rows(self.sessions,self.station[0]);self._save_active_workspace_state();settings_error=''
        try:self.persist_settings()
        except (StorageError,OSError,ValueError) as e:settings_error=' ／ 交信は保存済みですが、タブ状態の保存に失敗しました: '+str(e)
        self.e_status.setText(q.call+' を保存しました：'+str(path)+settings_error);self.easy_search()
        # EASY intentionally keeps only Band, Mode and My QTH for the next QSO.
        self.e_call.clear();self.e_his_qth.clear();self.e_code.clear();self.e_remarks.clear();self._easy_qso_date='';self._easy_prepared_call='';self.e_time.clear();self.e_date_label.setText('日付：----/--/--')
        self.easy_mode_changed();self.e_pages.setCurrentIndex(0);self.easy_update_path();self.e_call.setFocus()

    def _build_free_page(self):
        root=QWidget();root.setObjectName('mainRoot')
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(8,6,8,6);outer.setSpacing(6)

        station=QGroupBox('自局・フリラログファイル');self.free_stationbox=station
        sg=QGridLayout(station);sg.setContentsMargins(8,8,8,8);sg.setHorizontalSpacing(8);sg.setVerticalSpacing(4)
        sg.addWidget(QLabel('自局コールサイン'),0,0);sg.addWidget(QLabel('種類'),0,1);sg.addWidget(QLabel('機種名'),0,2)
        self.f_own=QLineEdit();self.f_own.setPlaceholderText('例：さいたまXX000')
        self.f_type=QComboBox();self.f_type.addItems(FREE_TYPES)
        self.f_model=QComboBox();self.f_model.setEditable(True);self.f_model.setPlaceholderText('自由入力・過去ログから候補')
        sg.addWidget(self.f_own,1,0);sg.addWidget(self.f_type,1,1);sg.addWidget(self.f_model,1,2)
        sg.addWidget(self.button('SET',self.free_set_station,True),1,3)
        self.f_path=PathLabel('自局コールサイン・種類をSETしてください');self.f_path.setObjectName('path');self.f_path.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        sg.addWidget(QLabel('現在のログファイル'),2,0);sg.addWidget(self.f_path,2,1,1,3)
        sg.setColumnStretch(0,3);sg.setColumnStretch(1,1);sg.setColumnStretch(2,3);sg.setColumnStretch(3,0);outer.addWidget(station)

        split=QHBoxLayout();outer.addLayout(split,1)
        self.free_entry=QGroupBox('フリラ交信入力');left=QVBoxLayout(self.free_entry);split.addWidget(self.free_entry,5)
        self.f_call=QLineEdit();self.f_call.setPlaceholderText('どこそこXX000');font=self.f_call.font();font.setBold(True);self.f_call.setFont(font)
        left.addWidget(QLabel('HIS CALLSIGN'));callrow=QHBoxLayout();callrow.addWidget(self.f_call,1);callrow.addWidget(self.button('RETURN',self.free_start_qso,True));left.addLayout(callrow)
        dg=QGridLayout();self.f_date=QLineEdit();self.f_time=QLineEdit();self.f_band=QLineEdit();self.f_mode=QLineEdit();self.f_band.setReadOnly(True);self.f_mode.setReadOnly(True)
        for col,(label,w) in enumerate((('Date',self.f_date),('Time · JST',self.f_time),('BAND',self.f_band),('MODE',self.f_mode))):dg.addWidget(QLabel(label),0,col);dg.addWidget(w,1,col);dg.setColumnStretch(col,1)
        left.addLayout(dg)
        rg=QGridLayout();self.f_sent=QLineEdit('59');self.f_received=QLineEdit('59');self.f_his_qth=QLineEdit();self.f_code=QLineEdit();self.f_my_qth=QLineEdit();self.f_remarks=QLineEdit()
        rg.addWidget(QLabel('RSTs（送信）'),0,0);rg.addWidget(QLabel('RSTr（受信）'),0,1);rg.addWidget(self.f_sent,1,0);rg.addWidget(self.f_received,1,1)
        rg.addWidget(QLabel('HIS QTH'),2,0);rg.addWidget(QLabel('JCC / JCG'),2,1);rg.addWidget(self.f_his_qth,3,0);rg.addWidget(self.f_code,3,1)
        rg.addWidget(QLabel('MY QTH'),4,0,1,2);rg.addWidget(self.f_my_qth,5,0,1,2);rg.addWidget(QLabel('RMKS'),6,0,1,2);rg.addWidget(self.f_remarks,7,0,1,2);left.addLayout(rg)
        left.addWidget(self.button('REC / RETURN　記録',self.free_record,True));left.addStretch()

        history=QGroupBox('LogSearch');self.free_history=history;hl=QVBoxLayout(history);split.addWidget(history,6)
        self.f_summary=QLabel('HIS CALLSIGNを入力してRETURN');hl.addWidget(self.f_summary)
        self.f_table=QTableWidget(0,7);self.f_table.setHorizontalHeaderLabels(['HIS CALLSIGN','日時 JST','種類','送 / 受','HIS QTH','RMKS','JCC/JCG'])
        self.f_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.f_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.f_table.verticalHeader().setVisible(False)
        self.f_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);self.f_table.horizontalHeader().setStretchLastSection(True);hl.addWidget(self.f_table)
        self.f_table.doubleClicked.connect(lambda index:self.show_free_history_detail(index.row()));self._free_history_visible=[]
        self.f_more=QLabel('同じ自局コールのCB/LCR/DCR等を横断して表示します');hl.addWidget(self.f_more)
        self.f_status=QLabel('フリラログは logbook_flr に保存します。');self.f_status.setObjectName('status');self.f_status.setWordWrap(True);hl.addWidget(self.f_status)

        self.f_type.currentTextChanged.connect(self._free_type_changed)
        self.f_call.returnPressed.connect(self.free_start_qso);self.f_remarks.returnPressed.connect(self.free_record)
        self.f_own.editingFinished.connect(lambda:self._normalize_free_editor(self.f_own,'自局コールサイン'))
        self.f_call.editingFinished.connect(lambda:self._normalize_free_editor(self.f_call,'相手コールサイン'))
        self.free_entry.setEnabled(False);root.setMinimumHeight(540);self._free_type_changed(self.f_type.currentText())
        return scroll

    def _normalize_free_editor(self,editor,label):
        raw=editor.text();converted=normalize_free_call(raw)
        if raw!=converted:
            # NFKC + Katakana -> Hiragana is intentional for free-radio calls.
            kana=any(('ァ'<=c<='ヶ') or ('ｦ'<=c<='ﾟ') for c in raw)
            editor.setText(converted)
            if kana:QMessageBox.information(self,label,'PSLogでは平仮名を使います。OK')

    def _refresh_free_model_suggestions(self,keep=''):
        kind=self.f_type.currentText() if hasattr(self,'f_type') else ''
        current=keep or (self.f_model.currentText() if hasattr(self,'f_model') else '')
        self.f_model.blockSignals(True);self.f_model.clear();self.f_model.addItems(free_models(self.repo,kind));self.f_model.setCurrentText(current);self.f_model.blockSignals(False)

    def _free_type_changed(self,kind):
        if not hasattr(self,'f_band'):return
        try:band,mode=radio_values(kind)
        except ValueError:band=mode='N/A'
        self.f_band.setText(band);self.f_mode.setText(mode);self._refresh_free_model_suggestions()

    def free_set_station(self):self._activate_free_station(True)

    def _activate_free_station(self,save_now):
        try:
            raw=self.f_own.text();call=validate_free_call(raw);kind=self.f_type.currentText();model=validate_model(self.f_model.currentText());radio_values(kind)
        except ValueError as e:QMessageBox.warning(self,'フリラ自局設定',str(e));return False
        if raw!=call and any(('ァ'<=c<='ヶ') or ('ｦ'<=c<='ﾟ') for c in raw):QMessageBox.information(self,'フリラ自局設定','PSLogでは平仮名を使います。OK')
        self.f_own.setText(call);self.f_model.setCurrentText(model);self.free_station=(call,kind,model);self.station=None;self.free_entry.setEnabled(True)
        session=self._active_workspace()
        if session.get('type')=='free':
            session.update(call=call,free_type=kind,model=model,my_qth=self.f_my_qth.text());self.session_tabs.setTabText(self.active_workspace_index,session_title(session))
        try:ensure_free_logbook(self.repo,call,kind,model,now_jst().strftime('%Y-%m-%d'))
        except (StorageError,OSError,ValueError) as e:QMessageBox.warning(self,'フリラログ作成',str(e));return False
        if save_now:
            try:self.persist_settings()
            except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'フリラ設定の保存',str(e))
        self.reload_free_logs();self.f_call.setFocus();return True

    def reload_free_logs(self):
        if self._active_workspace().get('type')!='free' or not self.free_station:return
        call,kind,model=self.free_station
        try:
            self.repo.recover();current=ensure_free_logbook(self.repo,call,kind,model,now_jst().strftime('%Y-%m-%d'))
            self.sessions={p:self.repo.open(p) for p in free_files(self.repo,call=call,kind=kind,model=model)}
            if current not in self.sessions:self.sessions[current]=self.repo.open(current)
            self.free_update_path();self.free_search_history()
        except (StorageError,OSError,ValueError) as e:QMessageBox.warning(self,'フリラログ読込',str(e))

    def free_update_path(self):
        if not self.free_station:return
        date=self.f_date.text().strip() or now_jst().strftime('%Y-%m-%d')
        try:self.f_path.setText(str(free_path(self.repo,*self.free_station,date)))
        except (ValueError,StorageError,OSError):self.f_path.setText('日付を正しく入力してください')

    def free_start_qso(self):
        if not self.free_station or not self.f_call.text().strip():self.f_call.setFocus();return
        try:call=validate_free_call(self.f_call.text(),'相手コールサイン')
        except ValueError as e:QMessageBox.warning(self,'入力確認',str(e));return
        self.f_call.setText(call);n=now_jst();self.f_date.setText(n.strftime('%Y-%m-%d'));self.f_time.setText(n.strftime('%H:%M'));self.f_sent.setText('59');self.f_received.setText('59');self.f_his_qth.clear();self.f_code.clear();self.f_remarks.clear();self.free_update_path();self.free_search_history();self.f_his_qth.setFocus()

    def free_record(self):
        if not self.free_station:return
        call,kind,model=self.free_station;band,mode=radio_values(kind)
        try:
            q=FreeQSO(self.f_date.text(),self.f_time.text(),band,mode,self.f_call.text(),self.f_sent.text(),self.f_received.text(),self.f_his_qth.text(),self.f_my_qth.text(),self.f_remarks.text(),self.f_code.text());q.validate()
            path=free_path(self.repo,call,kind,model,q.date);session=self.sessions.get(path) or self.repo.open(path);session.append(q);self.sessions[path]=session
        except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'保存できません',str(e));return
        self._save_active_workspace_state();settings_error=''
        try:self.persist_settings()
        except (StorageError,OSError,ValueError) as e:settings_error=' ／ タブ状態の保存に失敗しました: '+str(e)
        self.f_status.setText(q.call+' を保存しました：'+str(path)+settings_error);self.free_search_history();self.f_call.clear();self.f_his_qth.clear();self.f_code.clear();self.f_remarks.clear();self.f_date.clear();self.f_time.clear();self.f_call.setFocus()

    def free_search_history(self):
        if not self.free_station:return
        query=self.f_call.text().strip();self._free_history_visible=[]
        if not query:
            self.f_table.setRowCount(0);self.f_summary.setText('HIS CALLSIGNを入力してRETURN');return
        try:
            call=validate_free_call(query,'相手コールサイン');result=free_search(self.repo,FreeCriteria(self.free_station[0],call=call));hits=result.hits
        except (ValueError,StorageError,OSError):hits=[]
        self._free_history_visible=hits[:20];self.f_table.setRowCount(len(self._free_history_visible))
        for i,h in enumerate(self._free_history_visible):
            q=h.qso;values=[q.call,q.date+' '+q.time,getattr(h,'free_kind',''),q.sent+' / '+q.received,q.his_qth,q.remarks,q.code]
            for j,v in enumerate(values):self.f_table.setItem(i,j,QTableWidgetItem(v))
        self.f_summary.setText(f'{call} *　過去交信 {len(hits)}件');self.f_more.setText('他 '+str(len(hits)-len(self._free_history_visible))+'件' if len(hits)>len(self._free_history_visible) else '全種類のフリラログを横断しています')

    def show_free_history_detail(self,row=None):
        if row is None:row=self.f_table.currentRow()
        if not 0<=row<len(self._free_history_visible):return
        from free_search_ui import FreeEditDialog
        dialog=FreeEditDialog(self._free_history_visible[row],self);dialog.exec()
        if dialog.saved:self.reload_free_logs()

    def button(self,label,callback,primary=False):
        b=QPushButton(label); b.clicked.connect(callback)
        if primary:b.setObjectName('primary')
        return b

    def _build_contest_page(self):
        root=QWidget();root.setObjectName('mainRoot')
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(8,6,8,6);outer.setSpacing(6)

        station=QGroupBox('自局・コンテストログ');self.contest_stationbox=station
        grid=QGridLayout(station);grid.setContentsMargins(8,8,8,8);grid.setHorizontalSpacing(8);grid.setVerticalSpacing(4)
        self.c_own=QLineEdit();self.c_name=QLineEdit();self.c_name.setPlaceholderText('例：AADX')
        grid.addWidget(QLabel('自局コールサイン（/ 含む）'),0,0)
        grid.addWidget(QLabel('コンテスト英名'),0,1,1,2)
        c_path_head=QWidget();c_path_head_row=QHBoxLayout(c_path_head);c_path_head_row.setContentsMargins(0,0,0,0);c_path_head_row.setSpacing(6);c_path_head_row.addWidget(QLabel('現在のログファイル'));c_path_head_row.addStretch()
        self.c_show_current_log_button=QPushButton('全件表示');self.c_show_current_log_button.setObjectName('compactBlue');self.c_show_current_log_button.setFixedHeight(21);self.c_show_current_log_button.setToolTip('現在の自局コールとコンテストログを「ログ検索・編集」へ渡し、全件を表示します。');self.c_show_current_log_button.clicked.connect(lambda:self.open_current_log_search(True));c_path_head_row.addWidget(self.c_show_current_log_button,0,Qt.AlignmentFlag.AlignVCenter);grid.addWidget(c_path_head,0,3)
        grid.addWidget(self.c_own,1,0);grid.addWidget(self.c_name,1,1)
        grid.addWidget(self.button('SET',self.set_contest_station,True),1,2)
        self.c_path=PathLabel('自局コールサインとコンテスト英名をSETしてください');self.c_path.setObjectName('path')
        self.c_path.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter);grid.addWidget(self.c_path,1,3)
        grid.setColumnStretch(0,3);grid.setColumnStretch(1,3);grid.setColumnStretch(2,0);grid.setColumnStretch(3,6)
        outer.addWidget(station)

        split=QHBoxLayout();outer.addLayout(split,1)
        left=QVBoxLayout();split.addLayout(left,5)
        common=QGroupBox('共通設定');self.contest_common=common;cg=QGridLayout(common)
        self.c_band=QComboBox();self.c_band.setEditable(True);self.c_band.addItems(['0.135','0.475','1.8','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000'])
        self.c_mode=QComboBox();self.c_mode.setEditable(True);self.c_mode.addItems(['SSB','FM','AM','CW','RTTY','FT8','FT4','FT2','SSTV','FreeDV'])
        self.c_my_qth=QLineEdit()
        cg.addWidget(QLabel('Band · MHz'),0,0);cg.addWidget(QLabel('Mode'),0,1);cg.addWidget(QLabel('My QTH'),0,2)
        cg.addWidget(self.c_band,1,0);cg.addWidget(self.c_mode,1,1);cg.addWidget(self.c_my_qth,1,2)
        cg.setColumnStretch(0,2);cg.setColumnStretch(1,2);cg.setColumnStretch(2,5);left.addWidget(common)

        entry=QGroupBox('交信入力');self.contest_entry=entry;form=QVBoxLayout(entry)
        self.c_call_label=QLabel('相手コールサイン');c_call_label_font=self.c_call_label.font();c_call_label_font.setBold(True);self.c_call_label.setFont(c_call_label_font);form.addWidget(self.c_call_label)
        callrow=QHBoxLayout();self.c_call=QLineEdit();self.c_call.setPlaceholderText('JX1XXX')
        c_call_font=self.c_call.font();c_call_font.setBold(True);self.c_call.setFont(c_call_font);callrow.addWidget(self.c_call)
        callrow.addWidget(self.button('RETURN',self.contest_start_qso,True));form.addLayout(callrow)
        form.addWidget(QLabel('コンテストナンバー（RMKS）'))
        self.c_exchange=QLineEdit();self.c_exchange.setPlaceholderText('受信したコンテストナンバー');form.addWidget(self.c_exchange)
        detail=QGridLayout()
        self.c_date=QLineEdit();self.c_time=QLineEdit();self.c_sent=QLineEdit();self.c_received=QLineEdit()
        for col,(label,widget) in enumerate((('Date',self.c_date),('Time · JST',self.c_time),('His RST（送信）',self.c_sent),('My RST（受信）',self.c_received))):
            detail.addWidget(QLabel(label),0,col);detail.addWidget(widget,1,col);detail.setColumnStretch(col,1)
        form.addLayout(detail)
        form.addWidget(self.button('REC / RETURN　記録',self.contest_record,True))
        left.addWidget(entry,0)

        band_stats=QGroupBox('バンド別QSO数');self.contest_band_stats=band_stats
        band_stats_layout=QVBoxLayout(band_stats);band_stats_layout.setContentsMargins(8,7,8,7)
        self.c_band_counts=QLabel();self.c_band_counts.setTextFormat(Qt.TextFormat.RichText);self.c_band_counts.setWordWrap(True)
        band_stats_layout.addWidget(self.c_band_counts)
        left.addWidget(band_stats,0)
        left.addStretch(1)

        history=QGroupBox('LogSearch');self.contest_history=history;split.addWidget(history,6);hl=QVBoxLayout(history)
        self.c_limited=QCheckBox('検索範囲を選択中のログに限定');self.c_limited.setChecked(True);hl.addWidget(self.c_limited)
        self.c_summary=QLabel('相手コールサインを入力してRETURN');hl.addWidget(self.c_summary)
        self.c_table=QTableWidget(0,6);self.c_table.setHorizontalHeaderLabels(['相手コール','日時 JST','Band','Mode','送 / 受','コンテストナンバー'])
        self.c_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.c_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.c_table.verticalHeader().setVisible(False);self.c_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.c_table.horizontalHeader().setStretchLastSection(True);hl.addWidget(self.c_table)
        self.c_table.doubleClicked.connect(lambda index:self.show_contest_history_detail(index.row()))
        self._contest_history_visible=[]
        self.c_more=QLabel('このコンテストタブのTXTを表示します');hl.addWidget(self.c_more)
        self.c_status=QLabel('Call → コンテストナンバー → RETURN で高速記録できます。');self.c_status.setObjectName('status');self.c_status.setWordWrap(True);hl.addWidget(self.c_status)

        self.c_entry_country='';self._contest_prepared_call=''
        self.c_call.returnPressed.connect(self.contest_start_qso);self.c_call.textEdited.connect(lambda text:self._filter_amateur_callsign_editor(self.c_call,text));self.c_call.textChanged.connect(lambda:setattr(self,'blacklist_ack',None))
        self.c_call.editingFinished.connect(lambda:self.contest_start_qso() if normalize_callsign(self.c_call.text())!=self._contest_prepared_call else None)
        self.c_exchange.returnPressed.connect(self.contest_record);self.c_mode.currentTextChanged.connect(self.contest_mode_changed)
        self.c_exchange.editingFinished.connect(lambda:self.c_exchange.setText(machine_text(self.c_exchange.text(),upper=True)))
        for widget,kind in ((self.c_date,'date'),(self.c_time,'time'),(self.c_sent,'machine'),(self.c_received,'machine')):
            widget.editingFinished.connect(lambda widget=widget,kind=kind:self._normalize_contest_line(widget,kind))
        self.c_band.lineEdit().editingFinished.connect(lambda:self.c_band.setCurrentText(machine_text(self.c_band.currentText())))
        self.c_mode.lineEdit().editingFinished.connect(lambda:self.c_mode.setCurrentText(machine_text(self.c_mode.currentText(),upper=True)))
        self.c_band.currentTextChanged.connect(self.update_contest_band_counts)
        self.c_limited.toggled.connect(self.contest_scope_changed)
        self.c_date.textChanged.connect(lambda:self.update_contest_path() if self._active_workspace().get('type')=='contest' else None)
        self.setTabOrder(self.c_call,self.c_exchange)
        entry.setEnabled(False)
        # Same small-screen rule as the standard workspace: keep the compact
        # contest controls usable and let the QScrollArea scroll rather than
        # squeezing rows to unusable heights.
        root.setMinimumHeight(500)
        return scroll

    def _filter_amateur_callsign_editor(self,editor,text):
        filtered=amateur_callsign_entry(text)
        if filtered==text:
            return
        cursor=editor.cursorPosition()
        prefix=amateur_callsign_entry(text[:cursor])
        editor.setText(filtered);editor.setCursorPosition(len(prefix))

    def _active_workspace(self):
        if not self.workspace_sessions:
            self.workspace_sessions=[standard_session(1,self.settings)];self.active_workspace_index=0
        self.active_workspace_index=max(0,min(self.active_workspace_index,len(self.workspace_sessions)-1))
        return self.workspace_sessions[self.active_workspace_index]

    def _active_own_text(self):
        kind=self._active_workspace().get('type')
        if kind=='contest':return self.c_own.text() if hasattr(self,'c_own') else ''
        if kind=='easy':return self.e_own.text() if hasattr(self,'e_own') else ''
        if kind=='free':return self.f_own.text() if hasattr(self,'f_own') else ''
        return self.own.text() if hasattr(self,'own') else ''

    def _workspace_counts(self):
        standard=sum(s.get('type')=='standard' for s in self.workspace_sessions)
        contest=sum(s.get('type')=='contest' for s in self.workspace_sessions)
        return standard,contest

    def _easy_workspace_count(self):
        return sum(s.get('type')=='easy' for s in self.workspace_sessions)

    def _free_workspace_count(self):
        return sum(s.get('type')=='free' for s in self.workspace_sessions)

    def _rebuild_session_tabs(self):
        self._workspace_switching=True;self.session_tabs.blockSignals(True)
        try:
            while self.session_tabs.count():self.session_tabs.removeTab(0)
            for session in self.workspace_sessions:self.session_tabs.addTab(session_title(session))
            self.active_workspace_index=max(0,min(self.active_workspace_index,len(self.workspace_sessions)-1))
            self.session_tabs.setCurrentIndex(self.active_workspace_index)
        finally:
            self.session_tabs.blockSignals(False);self._workspace_switching=False
        self._update_session_tab_appearance()

    def _update_session_tab_appearance(self):
        closable=len(self.workspace_sessions)>1
        self.session_tabs.setTabsClosable(closable)
        by_id=contest_colors(self.workspace_sessions);indexed={}
        for i,session in enumerate(self.workspace_sessions):
            if session.get('type')=='contest' and session.get('id') in by_id:indexed[i]=by_id[session['id']]
        self.session_tabs.set_contest_colors(indexed)
        self.session_tabs.set_free_tabs(i for i,s in enumerate(self.workspace_sessions) if s.get('type')=='free')
        active=self._active_workspace()
        if active.get('type')=='contest':
            color=by_id.get(active.get('id'))
            if color:
                style=(f'QGroupBox {{border:2px solid {color["dark"]}; margin-top:8px; padding-top:6px; background:transparent;}}'
                       f'QGroupBox::title {{subcontrol-origin:margin; left:8px; padding:0 3px; color:{color["dark"]};}}')
                for box in (self.contest_common,self.contest_entry,self.contest_band_stats,self.contest_history):box.setStyleSheet(style)
        else:
            for box in (self.contest_common,self.contest_entry,self.contest_band_stats,self.contest_history):box.setStyleSheet('')

    def _save_active_workspace_state(self):
        if self._workspace_loading or not self.workspace_sessions:return
        session=self._active_workspace()
        if session.get('type')=='standard':
            session.update(call=self.own.text().strip().upper(),suffix=self.suffix.text(),
                band=self.text('band'),mode=self.text('mode'),my_qth=self.text('my_qth'),limited=self.limited.isChecked(),rmks2_visible=self.rmks2_toggle.isChecked())
        elif session.get('type')=='easy':
            session.update(call=self.e_own.text().strip().upper(),suffix='',
                band=self.e_band.currentText().strip(),mode=self.easy_mode_value(),my_qth=self.e_my_qth.text(),limited=self.e_limited.isChecked(),rmks2_visible=False)
        elif session.get('type')=='free':
            session.update(call=self.f_own.text().strip(),free_type=self.f_type.currentText(),model=self.f_model.currentText().strip(),my_qth=self.f_my_qth.text())
        else:
            try:name=clean_contest_name(self.c_name.text())
            except ValueError:name=session.get('contest_name','')
            if name:session['contest_name']=name
            session.update(call=self.c_own.text().strip().upper(),band=self.c_band.currentText().strip(),
                mode=self.c_mode.currentText().strip(),my_qth=self.c_my_qth.text(),limited=self.c_limited.isChecked())

    def _load_workspace(self,index,initial=False):
        if not self.workspace_sessions:
            self.workspace_sessions=[standard_session(1,self.settings)];index=0
        index=max(0,min(index,len(self.workspace_sessions)-1));self.active_workspace_index=index
        session=self.workspace_sessions[index];self._workspace_loading=True
        try:
            self.station=None;self.free_station=None;self.sessions={};self.rows=[];self.blacklist_ack=None
            if session.get('type')=='standard':
                self.page_stack.setCurrentWidget(self.standard_scroll)
                self.own.setText(session.get('call',''));self.suffix.setText(session.get('suffix',''))
                self.set_text('band',session.get('band','430'));self.set_text('mode',session.get('mode','FM'));self.set_text('my_qth',session.get('my_qth',''))
                self.call.clear()
                for key in ('date','time','his_qth','code','remarks'):self.set_text(key,'')
                self.rmks2.clear();self.rmks2_toggle.blockSignals(True);self.rmks2_toggle.setChecked(bool(session.get('rmks2_visible',False)));self.rmks2_toggle.blockSignals(False);self._apply_rmks2_visibility(self.rmks2_toggle.isChecked())
                self.mode_changed(self.text('mode'));self.limited.setChecked(bool(session.get('limited',False)))
                if self.own.text().strip():self._activate_station(False)
                else:
                    self.entry.setEnabled(False);self.path.setText('自局コールサインをSETしてください');self.table.setRowCount(0);self._update_current_log_buttons()
                if not initial:self.call.setFocus()
            elif session.get('type')=='easy':
                self.page_stack.setCurrentWidget(self.easy_scroll);self._easy_qso_date='';self._easy_prepared_call='';self.e_pages.setCurrentIndex(0)
                self.e_own.setText(session.get('call',''));self.e_band.setCurrentText(session.get('band','430'));self.easy_set_mode(session.get('mode','FM'));self.e_my_qth.setText(session.get('my_qth',''))
                self.e_call.clear();self.e_his_qth.clear();self.e_code.clear();self.e_remarks.clear();self.e_time.clear();self.e_date_label.setText('日付：----/--/--');self.e_limited.setChecked(bool(session.get('limited',False)));self.easy_mode_changed()
                if self.e_own.text().strip():self._activate_easy_station(False)
                else:
                    self.easy_entry.setEnabled(False);self.e_path.setText('自局コールサインをSETしてください');self.e_table.setRowCount(0);self._update_current_log_buttons()
                if not initial:self.e_call.setFocus()
            elif session.get('type')=='free':
                self.page_stack.setCurrentWidget(self.free_scroll)
                self.f_own.setText(session.get('call',''));self.f_type.setCurrentText(session.get('free_type','DCR'));self._refresh_free_model_suggestions(session.get('model',''));self.f_model.setCurrentText(session.get('model',''));self.f_my_qth.setText(session.get('my_qth',''))
                for e in (self.f_call,self.f_date,self.f_time,self.f_his_qth,self.f_code,self.f_remarks):e.clear()
                self.f_sent.setText('59');self.f_received.setText('59');self._free_type_changed(self.f_type.currentText())
                if self.f_own.text().strip():self._activate_free_station(False)
                else:
                    self.free_entry.setEnabled(False);self.f_path.setText('自局コールサイン・種類をSETしてください');self.f_table.setRowCount(0)
                if not initial:self.f_call.setFocus()
            else:
                self.page_stack.setCurrentWidget(self.contest_scroll)
                self.c_own.setText(session.get('call',''));self.c_name.setText(session.get('contest_name',''))
                self.c_band.setCurrentText(session.get('band','7'));self.c_mode.setCurrentText(session.get('mode','SSB'));self.c_my_qth.setText(session.get('my_qth',''))
                self.c_call.clear();self.c_exchange.clear();self.c_date.clear();self.c_time.clear();self.c_entry_country='';self._contest_prepared_call=''
                self.c_limited.setChecked(bool(session.get('limited',True)));self.contest_mode_changed(self.c_mode.currentText())
                if self.c_own.text().strip() and self.c_name.text().strip():self._activate_contest_station(False)
                else:
                    self.contest_entry.setEnabled(False);self.c_path.setText('自局コールサインとコンテスト英名をSETしてください');self.c_table.setRowCount(0);self.update_contest_band_counts();self._update_current_log_buttons()
                if not initial:self.c_call.setFocus()
        finally:
            self._workspace_loading=False
        self._update_session_tab_appearance()

    def _on_workspace_changed(self,index):
        if self._workspace_switching or index<0 or index>=len(self.workspace_sessions) or index==self.active_workspace_index:return
        self._save_active_workspace_state();self.active_workspace_index=index;self._load_workspace(index)
        self._persist_workspace_quiet()

    def _workspace_moved(self,old,new):
        if self._workspace_switching or old==new or not (0<=old<len(self.workspace_sessions) and 0<=new<len(self.workspace_sessions)):return
        self._save_active_workspace_state();active_id=self._active_workspace().get('id')
        item=self.workspace_sessions.pop(old);self.workspace_sessions.insert(new,item)
        self.active_workspace_index=next((i for i,s in enumerate(self.workspace_sessions) if s.get('id')==active_id),self.session_tabs.currentIndex())
        self._update_session_tab_appearance();self._persist_workspace_quiet()

    def _close_workspace(self,index):
        if len(self.workspace_sessions)<=1 or not 0<=index<len(self.workspace_sessions):return
        self._save_active_workspace_state();active_id=self._active_workspace().get('id');closing_active=self.workspace_sessions[index].get('id')==active_id
        closed=self.workspace_sessions.pop(index);snapshot=recent_snapshot(closed,self.settings.get('own',''));self.recent_workspace_sessions.insert(0,snapshot);self.recent_workspace_sessions=self.recent_workspace_sessions[:RECENT_LIMIT]
        if closing_active:
            self.active_workspace_index=min(index,len(self.workspace_sessions)-1)
        else:
            self.active_workspace_index=next((i for i,s in enumerate(self.workspace_sessions) if s.get('id')==active_id),0)
        self._rebuild_session_tabs()
        if closing_active:self._load_workspace(self.active_workspace_index)
        else:self._update_session_tab_appearance()
        self._persist_workspace_quiet()

    def _show_workspace_limit_message(self,workspace_type):
        if workspace_type=='standard':
            QMessageBox.information(self,'タブ追加','標準タブの上限に達しています。\n最大5個までです。')
        elif workspace_type=='easy':
            QMessageBox.information(self,'タブ追加','EASYタブの上限に達しています。\n最大2個までです。')
        elif workspace_type=='free':
            QMessageBox.information(self,'タブ追加','同時に開けるフリラタブは最大4個までです。\n既存のフリラタブを閉じてから呼び出してください。')
        else:
            QMessageBox.information(self,'タブ追加','コンテストタブの上限に達しています。\n最大6個までです。')

    def _show_add_session_menu(self):
        menu=QMenu(self)
        a_standard=menu.addAction('標準タブを追加');a_standard.triggered.connect(self._add_standard_workspace)
        a_easy=menu.addAction('EASYタブを追加');a_easy.triggered.connect(self._add_easy_workspace);a_easy.setEnabled(self._easy_workspace_count()<MAX_EASY)
        a_free=menu.addAction('フリラタブを追加…');a_free.triggered.connect(self._add_free_workspace);a_free.setEnabled(self._free_workspace_count()<MAX_FREE)
        a_contest=menu.addAction('コンテストタブを追加…');a_contest.triggered.connect(self._add_contest_workspace)
        if self.recent_workspace_sessions:
            recent=menu.addMenu('最近閉じたタブ20件')
            for position,session in enumerate(self.recent_workspace_sessions):
                if session.get('type')=='contest':
                    ym=session.get('event_ym','');ym_text=(ym[:4]+'/'+ym[4:]) if len(ym)==6 else ym
                    label=f'{session_title(session)} {ym_text} - {session.get("call","")}（コンテスト）'
                else:
                    label=session_title(session)
                action=recent.addAction(label);action.triggered.connect(lambda checked=False,p=position:self._reopen_recent_workspace(p))
        menu.exec(self.add_session_button.mapToGlobal(self.add_session_button.rect().bottomLeft()))

    def _inherit_workspace_values(self):
        self._save_active_workspace_state();s=self._active_workspace()
        # Amateur/EASY/contest tabs may inherit an amateur callsign from one
        # another, but a free-radio callsign is a different service identity.
        # Never prefill an amateur tab with the active free-radio callsign.
        call='' if s.get('type')=='free' else s.get('call','')
        return {'call':call,'band':s.get('band',self.settings.get('band','7')),
                'mode':s.get('mode',self.settings.get('mode','CW')),'my_qth':s.get('my_qth',self.settings.get('my_qth',''))}

    def _add_standard_workspace(self):
        slot=next_standard_slot(self.workspace_sessions)
        if slot is None:
            self._show_workspace_limit_message('standard');return
        base=self._inherit_workspace_values();session=standard_session(slot,{'own':base['call'],'suffix':'','band':'430','mode':'FM','my_qth':base['my_qth']})
        self.workspace_sessions.append(session);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self.own.setFocus();self.own.selectAll();self._persist_workspace_quiet()

    def _add_easy_workspace(self):
        slot=next_easy_slot(self.workspace_sessions)
        if slot is None:
            self._show_workspace_limit_message('easy');return
        base=self._inherit_workspace_values();session=easy_session(slot,{'own':base['call'],'suffix':'','band':base['band'],'mode':base['mode'],'my_qth':base['my_qth']})
        self.workspace_sessions.append(session);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self.e_own.setFocus();self.e_own.selectAll();self._persist_workspace_quiet()

    def _find_open_free_workspace(self,call,kind,model):
        for i,session in enumerate(self.workspace_sessions):
            if session.get('type')=='free' and session.get('call')==call and session.get('free_type')==kind and session.get('model')==model:return i
        return None

    def _add_free_workspace(self):
        if self._free_workspace_count()>=MAX_FREE:
            self._show_workspace_limit_message('free');return
        dialog=QDialog(self);dialog.setWindowTitle('フリラタブを追加')
        layout=QGridLayout(dialog);own=QLineEdit();kind=QComboBox();kind.addItems(FREE_TYPES);model=QComboBox();model.setEditable(True);model.setPlaceholderText('自由入力・過去ログから候補')
        if self._active_workspace().get('type')=='free':own.setText(self._active_workspace().get('call',''));kind.setCurrentText(self._active_workspace().get('free_type','DCR'))
        layout.addWidget(QLabel('自局コールサイン'),0,0);layout.addWidget(own,0,1)
        layout.addWidget(QLabel('種類'),1,0);layout.addWidget(kind,1,1)
        layout.addWidget(QLabel('機種名'),2,0);layout.addWidget(model,2,1)
        year=QLabel(now_jst().strftime('%Y')+'（年は自動）');layout.addWidget(QLabel('ログ年'),3,0);layout.addWidget(year,3,1)
        def models_changed(value):
            keep=model.currentText();model.clear();model.addItems(free_models(self.repo,value));model.setCurrentText(keep)
        kind.currentTextChanged.connect(models_changed);models_changed(kind.currentText())
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons,4,0,1,2);buttons.rejected.connect(dialog.reject)
        accepted={}
        def accept_free_dialog():
            raw=own.text()
            try:
                call=validate_free_call(raw)
            except ValueError as e:
                QMessageBox.warning(dialog,'フリラタブを追加',str(e))
                # Validation errors must never throw away what the user already typed.
                own.setFocus();own.selectAll();return
            ftype=kind.currentText()
            try:radio_values(ftype)
            except ValueError as e:
                QMessageBox.warning(dialog,'フリラタブを追加',str(e));kind.setFocus();return
            try:machine=validate_model(model.currentText())
            except ValueError as e:
                QMessageBox.warning(dialog,'フリラタブを追加',str(e));model.setFocus()
                if model.lineEdit():model.lineEdit().selectAll()
                return
            if raw!=call and any(('ァ'<=c<='ヶ') or ('ｦ'<=c<='ﾟ') for c in raw):
                QMessageBox.information(dialog,'フリラタブを追加','PSLogでは平仮名を使います。OK')
                own.setText(call)
            accepted.update(call=call,ftype=ftype,machine=machine)
            dialog.accept()
        buttons.accepted.connect(accept_free_dialog)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        call=accepted['call'];ftype=accepted['ftype'];machine=accepted['machine']
        existing=self._find_open_free_workspace(call,ftype,machine)
        if existing is not None:
            self.session_tabs.setCurrentIndex(existing);return
        slot=next_free_slot(self.workspace_sessions)
        if slot is None:self._show_workspace_limit_message('free');return
        try:ensure_free_logbook(self.repo,call,ftype,machine,now_jst().strftime('%Y-%m-%d'))
        except (StorageError,OSError,ValueError) as e:QMessageBox.warning(self,'フリラログ作成',str(e));return
        session=free_session(slot,call,ftype,machine,'');self.workspace_sessions.append(session);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self._persist_workspace_quiet()

    def recall_free_workspace(self):
        profiles=free_profiles(self.repo)
        if not profiles:
            QMessageBox.information(self,'フリラタブを呼び出す','呼び出せるフリラログブックがありません。\n新規作成は「＋タブ → フリラタブを追加…」から行えます。');return
        labels=[];mapping={}
        for p in profiles:
            years='/'.join(p['years']);model_label=p['model'] or '（機種名なし）';label=f"{p['call']} ｜ {p['kind']} ｜ {model_label} ｜ {years}"
            labels.append(label);mapping[label]=p
        selected,ok=QInputDialog.getItem(self,'フリラタブを呼び出す','ログブックを選択してください',labels,0,False)
        if not ok:return
        p=mapping[selected];existing=self._find_open_free_workspace(p['call'],p['kind'],p['model'])
        if existing is not None:
            self.session_tabs.setCurrentIndex(existing);return
        if self._free_workspace_count()>=MAX_FREE:
            self._show_workspace_limit_message('free');return
        slot=next_free_slot(self.workspace_sessions)
        if slot is None:self._show_workspace_limit_message('free');return
        self.workspace_sessions.append(free_session(slot,p['call'],p['kind'],p['model'],''));self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self._persist_workspace_quiet()

    def _add_contest_workspace(self):
        _,contest_count=self._workspace_counts()
        if contest_count>=MAX_CONTEST:
            self._show_workspace_limit_message('contest');return
        base=self._inherit_workspace_values();dialog=QDialog(self);dialog.setWindowTitle('コンテストタブを追加')
        layout=QGridLayout(dialog);call=QLineEdit(base['call']);name=QLineEdit();ym=QLineEdit(now_jst().strftime('%Y%m'))
        layout.addWidget(QLabel('自局コールサイン'),0,0);layout.addWidget(call,0,1)
        layout.addWidget(QLabel('コンテスト英名'),1,0);layout.addWidget(name,1,1)
        layout.addWidget(QLabel('対象年月（YYYYMM）'),2,0);layout.addWidget(ym,2,1)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons,3,0,1,2)
        while True:
            if dialog.exec()!=QDialog.DialogCode.Accepted:return
            try:
                station=validate_station(call.text(),'');contest_name=clean_contest_name(name.text());event_ym=clean_event_ym(ym.text())
            except ValueError as e:
                QMessageBox.warning(dialog,'入力確認',str(e));continue
            break
        session=contest_session(contest_name,event_ym,station,'7','SSB',base['my_qth'])
        self.workspace_sessions.append(session);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self._persist_workspace_quiet()

    def _reopen_recent_workspace(self,position):
        if not 0<=position<len(self.recent_workspace_sessions):return
        candidate=reopen_snapshot(self.recent_workspace_sessions[position],self.settings.get('own',''));standard_count,contest_count=self._workspace_counts()
        if candidate.get('type')=='standard':
            if standard_count>=MAX_STANDARD:
                self._show_workspace_limit_message('standard');return
            slot=candidate.get('slot');used={s.get('slot') for s in self.workspace_sessions if s.get('type')=='standard'}
            if slot in used:
                slot=next_standard_slot(self.workspace_sessions)
                if slot is None:
                    self._show_workspace_limit_message('standard');return
                candidate['slot']=slot
        elif candidate.get('type')=='easy':
            if self._easy_workspace_count()>=MAX_EASY:
                self._show_workspace_limit_message('easy');return
            slot=candidate.get('slot');used={s.get('slot') for s in self.workspace_sessions if s.get('type')=='easy'}
            if slot in used:
                slot=next_easy_slot(self.workspace_sessions)
                if slot is None:
                    self._show_workspace_limit_message('easy');return
                candidate['slot']=slot
        elif candidate.get('type')=='free':
            if self._free_workspace_count()>=MAX_FREE:
                self._show_workspace_limit_message('free');return
            # Do not reopen a second tab for the same free-radio log identity.
            for i,current in enumerate(self.workspace_sessions):
                if current.get('type')=='free' and all(current.get(k)==candidate.get(k) for k in ('call','free_type','model')):
                    self.active_workspace_index=i;self.session_tabs.setCurrentIndex(i);self._load_workspace(i);return
            slot=next_free_slot(self.workspace_sessions)
            if slot is None:self._show_workspace_limit_message('free');return
            candidate['slot']=slot
        elif candidate.get('type')=='contest':
            if contest_count>=MAX_CONTEST:
                self._show_workspace_limit_message('contest');return
        else:return
        self.recent_workspace_sessions.pop(position);self.workspace_sessions.append(candidate);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self._persist_workspace_quiet()

    def _persist_workspace_quiet(self):
        try:self.persist_settings()
        except (StorageError,OSError,ValueError) as e:
            kind=self._active_workspace().get('type');target=self.c_status if kind=='contest' else self.f_status if kind=='free' else self.e_status if kind=='easy' else self.status
            target.setText('タブ状態の保存に失敗しました: '+str(e))

    def _country_hint(self,call):
        if self._country_db is None:
            from countries import load
            self._country_db=load(self.data_root)
        return self._country_db.lookup(call)

    def _activate_contest_station(self,save_now):
        try:
            call=validate_station(self.c_own.text(),'');name=clean_contest_name(self.c_name.text())
            event_ym=clean_event_ym(self._active_workspace().get('event_ym',now_jst().strftime('%Y%m')))
        except ValueError as e:
            QMessageBox.warning(self,'自局・コンテスト設定',str(e));return False
        old=self._active_workspace().get('contest_name','')
        if old and old!=name:
            try:old_path=self.repo.path_for(call,contest_suffix(old,event_ym),self.c_date.text() or now_jst().strftime('%Y-%m-%d'))
            except ValueError:old_path=None
            if old_path and old_path.exists() and old_path.stat().st_size:
                if QMessageBox.question(self,'コンテスト英名の変更','コンテスト英名を変更すると新しいログファイルへ切り替わります。既存ログは移動しません。続けますか？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                    self.c_name.setText(old);return False
        self.c_own.setText(call);self.c_name.setText(name)
        if not self.c_my_qth.text().strip():
            try:
                hint=self._country_hint(call)
                if hint:self.c_my_qth.setText(hint['country'])
            except (StorageError,OSError):
                pass
        session=self._active_workspace()
        session.update(call=call,contest_name=name,event_ym=event_ym,band=self.c_band.currentText().strip(),mode=self.c_mode.currentText().strip(),my_qth=self.c_my_qth.text())
        self.station=(call,contest_suffix(name,event_ym));self.contest_entry.setEnabled(True)
        self.session_tabs.setTabText(self.active_workspace_index,name);self.reload_contest_logs();self.c_call.setFocus()
        if save_now:self._persist_workspace_quiet()
        return True

    def set_contest_station(self):
        self._activate_contest_station(True)

    def update_contest_path(self):
        if self._active_workspace().get('type')!='contest' or not self.station:return
        try:
            date=self.c_date.text().strip() or now_jst().strftime('%Y-%m-%d');path=self.repo.path_for(*self.station,date)
            if path not in self.sessions:self.sessions[path]=self.repo.open(path)
            self.c_path.setText(str(path))
        except (ValueError,StorageError,OSError):self.c_path.setText('日付・自局設定・コンテスト英名を確認してください')
        self._update_current_log_buttons()

    def reload_contest_logs(self):
        if self._active_workspace().get('type')!='contest' or not self.station:return
        try:
            self.repo.recover();self.sessions={}
            current_date=self.c_date.text().strip() or now_jst().strftime('%Y-%m-%d');current_path=self.repo.path_for(*self.station,current_date)
            paths=list(self.repo.files(self.station[0]))
            if current_path not in paths:paths.append(current_path)
            for path in paths:self.sessions[path]=self.repo.open(path)
            self.rows=session_rows(self.sessions,self.station[0])
            issues=sum(len(session.log.issues) for session in self.sessions.values())
            self._update_contest_scope_status()
            if issues:QMessageBox.warning(self,'ログの確認','解釈できない行のあるファイルは保存できません。audit.pyで行番号と理由を確認できます。')
            self.update_contest_path();self.contest_search();self.update_contest_band_counts()
        except (StorageError,OSError,ValueError) as e:QMessageBox.warning(self,'読み込み',str(e))

    def update_contest_band_counts(self,*_args):
        if not hasattr(self,'c_band_counts'):
            return
        current=(self.c_band.currentText().strip() if hasattr(self,'c_band') else '')
        counts={}
        if self._active_workspace().get('type')=='contest' and self.station:
            for owner,row in self.rows:
                if owner!=self.station:
                    continue
                band=(row.band or '').strip()
                if band:
                    counts[band]=counts.get(band,0)+1
        if current and current not in counts:
            counts[current]=0
        order=['0.135','0.475','1.8','1.9','3.5','7','10','14','18','21','24','28','50','144','430','1200','2400','5600','10000','24000','47000','77000']
        rank={value:i for i,value in enumerate(order)}
        def sort_key(value):
            if value in rank:
                return (0,rank[value])
            try:
                return (1,float(value))
            except ValueError:
                return (2,value)
        total=sum(count for band,count in counts.items() if count>0)
        ordered=[band for band in sorted(counts,key=sort_key) if counts[band]>0 or band==current]
        parts=[band_badge(band,counts[band]) for band in ordered]
        body='&nbsp;&nbsp;'.join(parts) if parts else '交信なし'
        self.c_band_counts.setText(body+'&nbsp;&nbsp;｜&nbsp;&nbsp;'+total_badge(total))

    def contest_mode_changed(self,mode):
        value=default_rst(mode) or ''
        self.c_sent.setText(value);self.c_received.setText(value)
        if not self._workspace_loading and self._active_workspace().get('type')=='contest':self._active_workspace()['mode']=self.c_mode.currentText().strip()

    def contest_start_qso(self):
        if self._active_workspace().get('type')!='contest':return
        call=normalize_callsign(self.c_call.text())
        if not call:self.c_call.setFocus();return
        self.c_call.setText(call);self._contest_prepared_call=call;self.blacklist_ack=None;self.warn_blacklist(call);now=now_jst()
        self.c_date.setText(now.strftime('%Y-%m-%d'));self.c_time.setText(now.strftime('%H:%M'))
        if not self.c_sent.text().strip() and not self.c_received.text().strip():self.contest_mode_changed(self.c_mode.currentText())
        self.c_entry_country='';country_note=''
        try:
            hint=self._country_hint(call)
            if hint:self.c_entry_country=hint['country'];country_note=' 国名は参照DBから記録します。'
        except (StorageError,OSError) as e:country_note=' 国名補助: '+str(e)
        self.update_contest_path();self.contest_search();self.c_exchange.setFocus();self.c_exchange.selectAll()
        self.c_status.setText(call+' をセットしました。コンテストナンバーを入力してRETURN。'+country_note)

    @staticmethod
    def _history_summary_html(base,count):
        if not base:
            return '相手コールサインを入力してRETURN'
        call=f'<span style="color:#185f38; background-color:#dff0e4; font-weight:600;">&nbsp;{base}&nbsp;</span>'
        return call+f' *　過去交信 {count}件'

    def _contest_scope_status_text(self):
        if self._active_workspace().get('type')!='contest' or not self.station:
            return ''
        limited=bool(self.c_limited.isChecked())
        if limited:
            count=sum(1 for owner,_row in self.rows if owner==self.station)
            issues=0
            for path,session in self.sessions.items():
                ident=file_identity(path)
                if ident and ident[1].split('/',1)[0]==self.station[0].split('/',1)[0] and ident[2]==self.station[1]:
                    issues+=len(session.log.issues)
            return f'選択中のコンテストログ：{count}交信 ／ 要確認行{issues}件。'
        issues=sum(len(session.log.issues) for session in self.sessions.values())
        return f'{self.station[0]} 全ログ：{len(self.rows)}交信 ／ 要確認行{issues}件。'

    def _update_contest_scope_status(self):
        text=self._contest_scope_status_text()
        if text:self.c_status.setText(text)

    def contest_scope_changed(self,*_args):
        self.contest_search();self._update_contest_scope_status()

    def contest_search(self):
        if self._active_workspace().get('type')!='contest' or not self.station:return
        call=self.c_call.text().strip().upper();base=call.split('/',1)[0] if call else ''
        def same(value):
            value=(value or '').strip().upper();return bool(base) and (value==base or value.startswith(base+'/'))
        current_owner=self.station
        candidates=[(owner,row) for owner,row in self.rows if same(row.call) and (not self.c_limited.isChecked() or owner==current_owner)]
        candidates.sort(key=lambda item:(item[1].date,item[1].time),reverse=True);visible=candidates[:20];self._contest_history_visible=visible;self.c_table.setRowCount(len(visible))
        for i,(_owner,row) in enumerate(visible):
            values=[row.call,row.date+' '+row.time,row.band,row.mode,row.sent+' / '+row.received,row.remarks]
            for j,value in enumerate(values):self.c_table.setItem(i,j,QTableWidgetItem(value))
        self.c_summary.setText(self._history_summary_html(base,len(candidates)) if call else self._history_summary_html('',0))
        self.c_more.setText('他 '+str(len(candidates)-len(visible))+'件' if len(candidates)>len(visible) else '選択中のコンテストログを表示しています')

    def _confirm_record_time(self,qso):
        now=now_jst()
        if not record_time_needs_confirmation(qso.date,qso.time,now,3):
            return 'normal'
        dialog=QDialog(self);dialog.setWindowTitle('記録時刻確認')
        layout=QVBoxLayout(dialog)
        message=QLabel('現在の時刻と3分以上ズレています。\n記録しますか？');message.setWordWrap(True);layout.addWidget(message)
        row=QHBoxLayout();row.addStretch()
        no=QPushButton('いいえ');current=QPushButton('現時刻で記録');yes=QPushButton('はい')
        no.setDefault(True);no.setAutoDefault(True);current.setAutoDefault(False);yes.setAutoDefault(False)
        choice={'value':'cancel'}
        def finish(value):
            choice['value']=value;dialog.accept()
        no.clicked.connect(lambda:finish('cancel'));current.clicked.connect(lambda:finish('current'));yes.clicked.connect(lambda:finish('keep'))
        row.addWidget(no);row.addWidget(current);row.addWidget(yes);layout.addLayout(row)
        dialog.exec()
        if choice['value']=='current':
            current_time=now_jst();qso.date=current_time.strftime('%Y-%m-%d');qso.time=current_time.strftime('%H:%M')
        return choice['value']

    def contest_record(self):
        if self._active_workspace().get('type')!='contest':return
        if not self.c_call.text().strip():self.c_call.setFocus();return
        if not self.station and not self._activate_contest_station(False):return
        if not self.c_date.text().strip() or not self.c_time.text().strip():
            now=now_jst();self.c_date.setText(now.strftime('%Y-%m-%d'));self.c_time.setText(now.strftime('%H:%M'))
        self.c_exchange.setText(machine_text(self.c_exchange.text(),upper=True))
        self.c_call.setText(normalize_callsign(self.c_call.text()))
        try:
            q=QSO(self.c_date.text().strip(),self.c_time.text().strip(),self.c_band.currentText().strip(),self.c_mode.currentText().strip(),
                self.c_call.text(),self.c_sent.text().strip(),self.c_received.text().strip(),self.c_entry_country,
                self.c_my_qth.text(),self.c_exchange.text().strip(),'');q.validate()
            self.c_date.setText(q.date);self.c_time.setText(q.time);self.c_band.setCurrentText(q.band);self.c_mode.setCurrentText(q.mode)
            self.c_sent.setText(q.sent);self.c_received.setText(q.received)
        except ValueError as e:
            QMessageBox.warning(self,'入力確認',str(e));return
        self.warn_blacklist(q.call)
        time_choice=self._confirm_record_time(q)
        if time_choice=='cancel':
            self.c_status.setText('現在時刻との差を確認するため記録を中止しました。')
            self.c_time.setFocus();self.c_time.selectAll();return
        if time_choice=='current':
            self.c_date.setText(q.date);self.c_time.setText(q.time);self.update_contest_path()
        if not q.remarks.strip():
            warning=QMessageBox(self)
            warning.setIcon(QMessageBox.Icon.Warning);warning.setWindowTitle('コンテストナンバー未入力')
            warning.setTextFormat(Qt.TextFormat.RichText)
            warning.setText('<span style="color:#b00020; font-weight:600;">コンテストナンバーが未入力ですが、このまま記録しますか？</span>')
            warning.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            warning.setDefaultButton(QMessageBox.StandardButton.No)
            if warning.exec()!=QMessageBox.StandardButton.Yes:
                self.c_status.setText('コンテストナンバーが未入力のため記録を中止しました。')
                self.c_exchange.setFocus();self.c_exchange.selectAll();return
        try:
            path=self.repo.path_for(*self.station,q.date);session=self.sessions.get(path) or self.repo.open(path);session.append(q);self.sessions[path]=session
        except (StorageError,OSError) as e:
            QMessageBox.warning(self,'保存できません',str(e));return
        self.rows=session_rows(self.sessions,self.station[0]);self._save_active_workspace_state()
        settings_error=''
        try:self.persist_settings()
        except (StorageError,OSError,ValueError) as e:settings_error=' ／ 交信は保存済みですが、タブ状態の保存に失敗しました: '+str(e)
        self.c_status.setText(q.call+' を保存しました：'+str(path)+settings_error);self.contest_search();self.update_contest_band_counts()
        self._contest_prepared_call='';self.c_call.clear();self.c_exchange.clear();self.c_entry_country=''
        self.contest_mode_changed(self.c_mode.currentText());self.c_call.setFocus()
    def tick(self):self.clock.setText(now_jst().strftime('%Y-%m-%d %H:%M:%S JST'))
    def _visible_status(self):
        kind=self._active_workspace().get('type')
        return self.c_status if kind=='contest' else self.f_status if kind=='free' else self.e_status if kind=='easy' else self.status
    def menus(self):
        self.menu_refs=[];self.action_refs=[]
        groups=[('ファイル',FILE_MENU_ITEMS),
          ('編集',['ログ検索・編集','ログ一括処理','QSL受領一括処理','ログファイル統合']),
          ('入出力',['インポート','エクスポート','特殊なエクスポート']),
          ('提出ログファイル作成',['コンテスト','アワード','QSOパーティ']),
          ('バックアップ',['今すぐバックアップ','全体バックアップから復元','ログバックアップから復元','バックアップ保存先を開く']),
          ('設定',['設定','ブラックリスト管理']),('フリラ',['フリラタブを呼び出す…','フリラログ検索・編集']),('ヘルプ',['使い方','PSLogフォーマットについて','起動コマンドフラグについて','PSLogをバージョンアップ','PSLogについて'])]
        for name,items in groups:
            menu=self.menuBar().addMenu(name)
            self.menu_refs.append(menu)
            for item in items:
                if item is None:
                    menu.addSeparator();continue
                if name=='提出ログファイル作成':
                    submenu=menu.addMenu(item);self.menu_refs.append(submenu)
                    if item=='コンテスト':
                        entries=[('コンテスト提出ログ作成…',self.open_contest),('コンテストルール表示…',self.open_contest_rule_view),('コンテストルール管理・編集…',self.open_rules),('Cabrillo出力テンプレート管理・編集…',self.open_templates)]
                    elif item=='アワード':
                        entries=[('アワード申請用ログ作成…',self.open_award),('アワード条件表示…',self.open_award_condition_view),('JCC/JCG交信チェック…',self.open_jccjcg_award_check)]
                    else:
                        entries=[('QSOパーティ提出ログ作成…',self.open_qso_party),('QSOパーティルール表示…',self.open_party_rule_view)]
                    for label,callback in entries:
                        action=submenu.addAction(label);action.triggered.connect(callback);self.action_refs.append(action)
                    continue
                if name=='編集' and item=='ログ一括処理':
                    batch_menu=menu.addMenu(item);self.menu_refs.append(batch_menu)
                    action=batch_menu.addAction('JCC/JCG…');action.triggered.connect(self.open_jccjcg_batch);self.action_refs.append(action)
                    continue
                if item=='特殊なエクスポート':
                    special=menu.addMenu(item);self.menu_refs.append(special)
                    action=special.addAction('POTA提出用ADIFファイル');action.triggered.connect(self.open_pota);self.action_refs.append(action)
                    action=special.addAction('SOTA提出用CSVファイル');action.triggered.connect(self.open_sota);self.action_refs.append(action)
                    continue
                action=menu.addAction(item)
                self.action_refs.append(action)
                if item=='PSLog終了':action.triggered.connect(self.close)
                elif item=='PSLog再起動':action.triggered.connect(self.restart_pslog)
                elif item=='ログを再読込':action.triggered.connect(self.reload_logs)
                elif item=='ログ検索・編集':action.triggered.connect(self.open_search)
                elif item=='フリラタブを呼び出す…':action.triggered.connect(self.recall_free_workspace)
                elif item=='フリラログ検索・編集':action.triggered.connect(self.open_free_search)
                elif item=='QSL受領一括処理':action.triggered.connect(self.open_qsl)
                elif item=='ログファイル統合':action.triggered.connect(self.open_log_merge)
                elif item=='コンテスト提出ログ作成':action.triggered.connect(self.open_contest)
                elif item=='コンテストルール管理・編集':action.triggered.connect(self.open_rules)
                elif item=='Cabrillo出力テンプレート管理・編集':action.triggered.connect(self.open_templates)
                elif item=='ログバックアップから復元':action.triggered.connect(self.open_restore)
                elif item=='全体バックアップから復元':action.triggered.connect(self.open_full_restore)
                elif item=='インポート':action.triggered.connect(self.open_import)
                elif item=='エクスポート':action.triggered.connect(self.open_export)
                elif item=='ブラックリスト管理':action.triggered.connect(self.open_blacklist)
                elif item=='設定':action.triggered.connect(self.open_settings)
                elif item=='今すぐバックアップ':action.triggered.connect(self.full_backup)
                elif item=='PSLogをバージョンアップ':action.triggered.connect(self.open_update)
                elif item in ('使い方','PSLogフォーマットについて','起動コマンドフラグについて','PSLogについて'):
                    from help_ui import HelpDialog
                    action.triggered.connect(lambda checked=False,topic=item:HelpDialog(topic,self).exec())
                elif item in ('本体の場所を開く','ログファイルの場所を開く','出力ファイルの場所を開く','レポートの場所を開く','バックアップ保存先を開く'):
                    folders={
                        '本体の場所を開く':self.data_root,
                        'ログファイルの場所を開く':self.repo.book,
                        '出力ファイルの場所を開く':self.repo.output,
                        'レポートの場所を開く':self.repo.root/'reports',
                        'バックアップ保存先を開く':self.repo.bak,
                    }
                    action.triggered.connect(lambda checked=False,p=folders[item]:open_folder(self,p))
                else:action.setEnabled(False);action.setToolTip('今後実装・接続予定')
    def restart_pslog(self):
        self._restart_requested=True
        if not self.close():self._restart_requested=False

    def current_settings(self):
        self._save_active_workspace_state()
        values=dict(self.settings)
        if self.isVisible():values['window_geometry']=window_state(self)
        primary=next((s for s in self.workspace_sessions if s.get('type')=='standard'),next((s for s in self.workspace_sessions if s.get('type')=='easy'),None))
        # conf.cfg's legacy own/suffix/band/mode fields are amateur-radio
        # defaults.  A free-only user must not have a Japanese free-radio call
        # written into ``own`` merely because the active tab is free-radio.
        if primary is None:
            own=self.settings.get('own','');suffix=self.settings.get('suffix','')
            band=self.settings.get('band','');mode=self.settings.get('mode','')
            my_qth=self._active_workspace().get('my_qth',self.settings.get('my_qth',''))
        else:
            own=primary.get('call','');suffix=primary.get('suffix','')
            band=primary.get('band','');mode=primary.get('mode','');my_qth=primary.get('my_qth','')
        values.update({'version':VERSION,'own':own,'suffix':suffix,'my_qth':my_qth,
            'band':band,'mode':mode,
            'keep_band':self.keep_band.isChecked(),'keep_mode':self.keep_mode.isChecked(),'auto_rst':self.auto_rst.isChecked(),'location_assist':self.location_on.isChecked(),
            'workspace_sessions':[serializable(session) for session in self.workspace_sessions],
            'active_workspace_id':self._active_workspace().get('id',''),
            'recent_workspace_sessions':[serializable(session) for session in self.recent_workspace_sessions[:RECENT_LIMIT]]})
        return values
    def persist_settings(self,values=None):
        data=self.current_settings()
        if values is not None:data.update(values)
        data=validate_preferences(data)
        save_settings(self.data_root,data,self.config_snapshot)
        self.config_snapshot=Snapshot.read(self.config_path);self.settings=data
    def apply_preferences(self,values):
        self.persist_settings(values)
        self.repo.backup_keep=self.settings['backup_keep']
        self.location_on.setChecked(self.settings['location_assist'])
        for key in ('keep_band','keep_mode','auto_rst'):getattr(self,key).setChecked(self.settings[key])
    def open_settings(self):
        from settings_ui import SettingsDialog
        SettingsDialog(self.current_settings(),self.apply_preferences,self,repo=self.repo).exec()
    def full_backup(self):
        from full_backup import create
        suggested='PSLog_backup_'+now_jst().strftime('%Y%m%d-%H%M%S')+'.zip'
        default_path=str(self.data_root.parent/suggested)
        destination,_=QFileDialog.getSaveFileName(
            self,'全体バックアップの保存先（別ドライブやUSBメモリーを推奨）',
            default_path,'PSLogバックアップ (*.zip)'
        )
        if not destination:return None
        if not destination.lower().endswith('.zip'):destination+='.zip'
        try:
            self.persist_settings();path,count=create(self.repo,destination)
        except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'バックアップ',str(e));return None
        self._visible_status().setText(f'{count}ファイルをバックアップしました: {path}')
        return path,count
    def monthly_backup_notice(self):
        if not self.isVisible() or not self.settings['monthly_backup']:return
        month=now_jst().strftime('%Y-%m')
        if self.settings.get('monthly_notice')==month:return
        create_now=False
        if list(self.repo.book.glob('*.txt')):
            message=QMessageBox(self);message.setWindowTitle('月替わりのバックアップ')
            message.setText('ログと設定の全体バックアップを、別ドライブやUSBメモリーへ保存しておきませんか？')
            create_button=message.addButton('今すぐ作成',QMessageBox.ButtonRole.AcceptRole)
            skip=message.addButton('今回は見送る',QMessageBox.ButtonRole.RejectRole);message.setDefaultButton(skip)
            message.exec();create_now=message.clickedButton()==create_button
        try:self.persist_settings({'monthly_notice':month})
        except (ValueError,StorageError,OSError) as e:QMessageBox.warning(self,'月次案内の保存',str(e));return
        if create_now:self.full_backup()
    def open_update(self):
        if sys.platform!='win32' or not getattr(sys,'frozen',False):
            QMessageBox.information(self,'PSLogのバージョンアップ',
                'この機能はWindowsビルド版PSLogで使用できます。\n開発用ソース実行では更新を行いません。')
            return
        intro=QMessageBox(self);intro.setWindowTitle('PSLogのバージョンアップ');intro.setIcon(QMessageBox.Icon.Information)
        intro.setText(f'現在のバージョン：PSLog Ver{VERSION}')
        intro.setInformativeText(
            'PSLogを新しいバージョンへ更新したり、同じバージョンを修復・再インストールできます。\n\n'
            '新しいPSLogのWindows版ZIPファイルを、展開せずZIPのまま指定してください。\n'
            '通常配布されている「PSLog_xxx_Windows_....zip」をそのまま使用できます。\n\n'
            'バージョンアップではPSLog本体と関連プログラムを更新します。\n'
            'ログ・設定などの利用者データは保持されます。\n\n'
            '更新前には「今すぐバックアップ」で全体バックアップを必ず作成します。\n'
            '問題が起きた場合は、正常な新しいPSLogを用意し、\n'
            '「バックアップ → 全体バックアップから復元」で更新直前の状態へ戻せます。\n\n'
            '現在と同じバージョンでも、内容が異なる正式ZIPは修復・再インストールできます。\n'
            '現在と同じ内容のZIPは再インストールせず、古いバージョンへ戻す更新はできません。')
        choose=intro.addButton('更新ZIPを選択…',QMessageBox.ButtonRole.AcceptRole)
        cancel=intro.addButton('キャンセル',QMessageBox.ButtonRole.RejectRole);intro.setDefaultButton(choose)
        intro.exec()
        if intro.clickedButton()!=choose:return
        source,_=QFileDialog.getOpenFileName(self,'新しいPSLog Windows版ZIPを選択','','PSLog Windows版 (*.zip)')
        if not source:return
        try:
            from update_package import (
                inspect_update,classify_update,UPDATE_UPGRADE,UPDATE_REINSTALL,
                UPDATE_SAME,UPDATE_DOWNGRADE,
            )
            info=inspect_update(source)
            update_mode=classify_update(info,VERSION,self.data_root)
        except (StorageError,OSError,ValueError) as e:
            QMessageBox.warning(self,'PSLogのバージョンアップ',str(e));return
        if update_mode==UPDATE_DOWNGRADE:
            QMessageBox.warning(self,'PSLogのバージョンアップ',
                f'Ver{VERSION} から Ver{info.version} へ戻すことはできません。\n新しいバージョンを選択してください。')
            return
        if update_mode==UPDATE_SAME:
            QMessageBox.information(self,'PSLogのバージョンアップ',
                f'選択したZIPは現在の PSLog Ver{VERSION} と同じ内容です。\n再インストールは必要ありません。')
            return
        if update_mode==UPDATE_REINSTALL:
            repair=QMessageBox(self);repair.setWindowTitle('PSLogの修復・再インストール');repair.setIcon(QMessageBox.Icon.Warning)
            repair.setText(f'現在と同じ PSLog Ver{VERSION} です。')
            repair.setInformativeText(
                '選択されたパッケージは、現在インストールされている内容と異なります。\n\n'
                '修復・再インストールとして同じバージョンを上書きしますか？')
            reinstall=repair.addButton('再インストール',QMessageBox.ButtonRole.AcceptRole)
            repair_cancel=repair.addButton('キャンセル',QMessageBox.ButtonRole.RejectRole);repair.setDefaultButton(reinstall)
            repair.exec()
            if repair.clickedButton()!=reinstall:return

        confirm=QMessageBox(self);confirm.setWindowTitle('PSLogのバージョンアップ確認');confirm.setIcon(QMessageBox.Icon.Warning)
        if update_mode==UPDATE_REINSTALL:
            confirm.setText(f'PSLog Ver{VERSION} を修復・再インストール')
        else:
            confirm.setText(f'PSLog Ver{VERSION} → Ver{info.version}')
        confirm.setInformativeText(
            '更新前に全体バックアップが必要です。\n'
            '「今すぐバックアップ」を押して保存先を指定してください。\n\n'
            'バックアップが正常に作成できた場合だけ、そのまま更新を開始します。\n'
            'キャンセルした場合は更新しません。')
        backup_button=confirm.addButton('今すぐバックアップ',QMessageBox.ButtonRole.AcceptRole)
        cancel_button=confirm.addButton('キャンセル',QMessageBox.ButtonRole.RejectRole);confirm.setDefaultButton(backup_button)
        confirm.exec()
        if confirm.clickedButton()!=backup_button:return
        backup=self.full_backup()
        if not backup:
            QMessageBox.information(self,'PSLogのバージョンアップ','全体バックアップが作成されなかったため、バージョンアップを中止しました。')
            return
        backup_path,count=backup
        try:
            # Flush normal end-of-session log backups before handing control to
            # the external updater.  The user-visible full backup above is the
            # documented recovery path; updater rollback is only a temporary
            # program-file transaction aid.
            self.persist_settings()
            errors=self.repo.close()
            if errors:raise StorageError('更新前のログバックアップに失敗しました。'+str(errors))
            from update_launcher import launch_update
            launch_update(self.data_root,source,VERSION,mode=update_mode)
        except (StorageError,OSError,ValueError) as e:
            QMessageBox.critical(self,'PSLogのバージョンアップ',
                str(e)+'\n\n更新を開始していません。現在のPSLogをそのまま使用できます。')
            return
        QMessageBox.information(self,'PSLogのバージョンアップ',
            f'更新準備ができました。PSLogを終了します。\n\n'
            f'全体バックアップ ({count}ファイル):\n{backup_path}\n\n'
            + ('この後PSLogUpdater.exeが本体を修復・再インストールします。\n' if update_mode==UPDATE_REINSTALL else 'この後PSLogUpdater.exeが本体を更新します。\n')
            + '完了画面でOKを押すか、約10秒待つとPSLogが起動します。')
        self._update_exit=True
        self.close()

    def open_blacklist(self):
        from blacklist_ui import BlacklistDialog
        BlacklistDialog(self.data_root,self).exec()
        self.blacklist_ack=None
    def warn_blacklist(self,call):
        from blacklist import Blacklist
        try:entries=Blacklist(self.data_root).matching(call)
        except (StorageError,OSError) as e:
            QMessageBox.warning(self,'ブラックリスト確認',str(e)+'\n今回は照合できません。交信記録は継続できます。');return
        signature=(call,tuple(entries))
        if entries and signature!=self.blacklist_ack:
            QMessageBox.warning(self,'ブラックリストの警告',call+' はブラックリストに一致しました。\n\n'+'\n'.join(e.call+': '+e.memo for e in entries)+'\n\nOKで閉じて、そのまま操作を続けられます。',QMessageBox.StandardButton.Ok)
        self.blacklist_ack=signature
    def _current_log_target(self,contest=False):
        if contest:
            if self._active_workspace().get('type')!='contest' or not self.station or not self.c_own.text().strip():return None
            date=self.c_date.text().strip() or now_jst().strftime('%Y-%m-%d')
        else:
            kind=self._active_workspace().get('type')
            if kind not in ('standard','easy') or not self.station or not self._active_own_text().strip():return None
            date=(self._easy_qso_date or now_jst().strftime('%Y-%m-%d')) if kind=='easy' else (self.text('date') or now_jst().strftime('%Y-%m-%d'))
        try:return self.station[0],self.repo.path_for(*self.station,date)
        except (ValueError,StorageError,OSError):return None
    def _update_current_log_buttons(self):
        if hasattr(self,'show_current_log_button'):self.show_current_log_button.setEnabled(self._current_log_target(False) is not None)
        if hasattr(self,'e_show_current_log_button'):self.e_show_current_log_button.setEnabled(self._current_log_target(False) is not None)
        if hasattr(self,'c_show_current_log_button'):self.c_show_current_log_button.setEnabled(self._current_log_target(True) is not None)
    def open_current_log_search(self,contest=False):
        target=self._current_log_target(contest)
        if not target:return
        own,path=target
        from search_ui import SearchDialog
        dialog=SearchDialog(self.repo,own,self,filename=path.name,autorun=True)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()

    def open_export(self):
        from export_ui import ExportDialog
        ExportDialog(self.repo,self.station[0] if self.station else '',self).exec()
    def open_contest(self):
        from contest_ui import ContestDialog
        ContestDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self).exec()
    def open_qso_party(self):
        from activity_ui import ActivityDialog
        ActivityDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self).exec()
    def open_award(self):
        from activity_ui import ActivityDialog
        ActivityDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self,award=True).exec()
    def open_contest_rule_view(self):
        from rule_view_ui import ContestRuleViewDialog
        ContestRuleViewDialog(self.data_root,self).exec()
    def open_party_rule_view(self):
        from rule_view_ui import PartyRuleViewDialog
        PartyRuleViewDialog(self).exec()
    def open_award_condition_view(self):
        from rule_view_ui import AwardConditionViewDialog
        AwardConditionViewDialog(self.data_root,self).exec()
    def open_jccjcg_award_check(self):
        from jccjcg_award_check_ui import JccJcgAwardCheckDialog
        JccJcgAwardCheckDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self).exec()
    def open_templates(self):
        from cabrillo_template_ui import TemplatesDialog
        TemplatesDialog(self.repo.root,self).exec()
    def open_rules(self):
        from contest_rule_ui import RulesDialog
        RulesDialog(self.repo.root,self).exec()
    def open_sota(self):
        from sota_ui import SotaDialog
        SotaDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self).exec()
    def open_pota(self):
        from pota_ui import PotaDialog
        PotaDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self).exec()
    def open_jccjcg_batch(self):
        from jccjcg_batch_ui import JccJcgBatchDialog
        dialog=JccJcgBatchDialog(self.repo,self.station[0] if self.station else '',self)
        dialog.exec()
        if dialog.saved:self.reload_logs()

    def open_qsl(self):
        from qsl_ui import QSLDialog
        dialog=QSLDialog(self.repo,self.station[0] if self.station else self._active_own_text(),self)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()
    def open_log_merge(self):
        from log_merge_ui import LogMergeDialog
        dialog=LogMergeDialog(self.repo,self)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()
    def open_import(self):
        from import_ui import ImportDialog
        dialog=ImportDialog(self.repo,self.station[0] if self.station else '',self)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()
    def open_restore(self):
        from restore_ui import RestoreDialog
        dialog=RestoreDialog(self.repo,self)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()
    def open_full_restore(self):
        from full_restore import inspect_backup,restore
        source,_=QFileDialog.getOpenFileName(self,'全体バックアップZIPを選択','','PSLogバックアップ (*.zip)')
        if not source:return
        try:plan=inspect_backup(self.repo,source)
        except (StorageError,OSError,ValueError) as e:
            QMessageBox.warning(self,'全体バックアップから復元',str(e));return
        kind='旧形式（manifestなし）' if plan.legacy else f'形式 {plan.format_version}'
        legacy_note=''
        if plan.legacy_conflicts:
            legacy_note=(f'\n\n旧形式のため標準ファイルと区別できない {len(plan.legacy_conflicts)}件は、'
                         '現行版を上書きせず別フォルダーへ保存します。')
        text=(f'バックアップ作成PSLog: {plan.source_version}\n'
              f'作成日時: {plan.created_at}\n'
              f'バックアップ形式: {kind}\n'
              f'復元対象: {len(plan.active)}ファイル\n'
              f'現行版の標準ファイルとして維持: {len(plan.skipped_bundled)}ファイル'
              f'{legacy_note}\n\n'
              'ログブックとユーザー設定をこのバックアップへ復元します。\n'
              '復元直前の現在状態は bak/full-restore-safety に自動保存します。\n'
              '復元後は設定を確実に読み直すためPSLogを終了します。続けますか？')
        answer=QMessageBox.warning(self,'全体バックアップの復元確認',text,
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        try:
            # Include the current visible settings in the automatic safety ZIP.
            self.persist_settings();result=restore(self.repo,plan)
        except (StorageError,OSError,ValueError) as e:
            QMessageBox.critical(self,'全体バックアップの復元',
                str(e)+'\n\n復元処理を完了できませんでした。現在状態の安全バックアップが作成済みの場合は bak/full-restore-safety を確認してください。')
            return
        self._full_restore_exit=True
        safety_text=str(result['safety_backup']) if result['safety_backup'] else '復元前の利用者データなし（新規状態）'
        message=(f'全体バックアップを復元しました。\n\n復元元PSLog: {result["source_version"]}\n'
                 f'復元ファイル: {result["restored"]}件\n'
                 f'復元直前の安全バックアップ:\n{safety_text}')
        if result['legacy_conflicts']:
            message+=f'\n\n旧形式ZIPの要確認ファイル {result["legacy_conflicts"]}件を保存しました:\n{result["legacy_conflict_folder"]}'
        message+='\n\nPSLogを終了します。再起動すると復元後の設定とログを読み込みます。'
        QMessageBox.information(self,'全体バックアップから復元',message)
        self.close()
    def open_free_search(self):
        from free_search_ui import FreeSearchDialog
        own=self._active_own_text() if self._active_workspace().get('type')=='free' else ''
        dialog=FreeSearchDialog(self.repo,own,self);dialog.exec()
        if self._active_workspace().get('type')=='free' and self.free_station:self.reload_free_logs()

    def open_search(self):
        from search_ui import SearchDialog
        kind=self._active_workspace().get('type')
        own=(self.station[0] if self.station else self._active_own_text()) if kind in ('standard','easy','contest') else ''
        dialog=SearchDialog(self.repo,own,self)
        dialog.logs_changed.connect(self.reload_logs)
        dialog.exec()
    def first_start(self):
        """First-run service selector: amateur radio by default, free-radio optional."""
        dialog=QDialog(self);dialog.setWindowTitle('初回起動');dialog.setModal(True)
        layout=QVBoxLayout(dialog);layout.setContentsMargins(16,14,16,14);layout.setSpacing(8)
        prompt=QLabel('アマチュア無線のコールサイン');prompt_font=prompt.font();prompt_font.setBold(True);prompt.setFont(prompt_font);layout.addWidget(prompt)
        call=QLineEdit();call.setPlaceholderText('JH1HST');layout.addWidget(call)
        switch=QPushButton('アマチュア無線ではなくフリラのコールサイン');layout.addWidget(switch)

        free_box=QGroupBox('フリラログの設定');free_grid=QGridLayout(free_box)
        kind=QComboBox();kind.addItems(FREE_TYPES)
        model=QComboBox();model.setEditable(True);model.setPlaceholderText('任意・自由入力・過去ログから候補')
        free_grid.addWidget(QLabel('種類'),0,0);free_grid.addWidget(kind,0,1)
        free_grid.addWidget(QLabel('機種名（任意）'),1,0);free_grid.addWidget(model,1,1)
        free_grid.addWidget(QLabel('ログ年'),2,0);free_grid.addWidget(QLabel(now_jst().strftime('%Y')+'（年は自動）'),2,1)
        free_box.hide();layout.addWidget(free_box)

        def models_changed(value):
            keep=model.currentText();model.clear();model.addItems(free_models(self.repo,value));model.setCurrentText(keep)
        kind.currentTextChanged.connect(models_changed);models_changed(kind.currentText())

        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        start_button=buttons.button(QDialogButtonBox.StandardButton.Ok)
        if start_button:start_button.setText('開始')
        buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        state={'free':False};accepted={}

        def set_free_mode(on):
            state['free']=bool(on);free_box.setVisible(state['free'])
            if state['free']:
                prompt.setText('フリラのコールサイン');call.setPlaceholderText('さいたまXX000')
                switch.setText('フリラではなくアマチュア無線のコールサイン')
            else:
                prompt.setText('アマチュア無線のコールサイン');call.setPlaceholderText('JH1HST')
                switch.setText('アマチュア無線ではなくフリラのコールサイン')
            dialog.adjustSize();call.setFocus();call.selectAll()
        switch.clicked.connect(lambda:set_free_mode(not state['free']))

        def accept_start():
            if not state['free']:
                try:station_call=validate_station(call.text(),'')
                except ValueError as e:
                    QMessageBox.warning(dialog,'初回起動',str(e));call.setFocus();call.selectAll();return
                accepted.update(mode='amateur',call=station_call);dialog.accept();return
            raw=call.text()
            try:
                free_call=validate_free_call(raw);free_type=kind.currentText();radio_values(free_type);machine=validate_model(model.currentText())
            except ValueError as e:
                QMessageBox.warning(dialog,'初回起動',str(e));call.setFocus();call.selectAll();return
            if raw!=free_call and any(('ァ'<=c<='ヶ') or ('ｦ'<=c<='ﾟ') for c in raw):
                QMessageBox.information(dialog,'初回起動','PSLogでは平仮名を使います。OK');call.setText(free_call)
            try:ensure_free_logbook(self.repo,free_call,free_type,machine,now_jst().strftime('%Y-%m-%d'))
            except (StorageError,OSError,ValueError) as e:
                QMessageBox.warning(dialog,'初回起動','フリラログを作成できません。\n'+str(e));return
            accepted.update(mode='free',call=free_call,free_type=free_type,model=machine);dialog.accept()
        buttons.accepted.connect(accept_start)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return

        if accepted['mode']=='amateur':
            if self._active_workspace().get('type')=='easy':self.e_own.setText(accepted['call']);self.easy_set_station()
            else:self.own.setText(accepted['call']);self.set_station()
            return

        free_call=accepted['call'];free_type=accepted['free_type'];machine=accepted['model']
        existing=self._find_open_free_workspace(free_call,free_type,machine)
        if existing is not None:
            self.session_tabs.setCurrentIndex(existing);return
        slot=next_free_slot(self.workspace_sessions)
        if slot is None:self._show_workspace_limit_message('free');return
        session=free_session(slot,free_call,free_type,machine,'')
        active=self._active_workspace();replace_initial=(len(self.workspace_sessions)==1 and active.get('type') in ('standard','easy') and not active.get('call','').strip())
        if replace_initial:
            self.workspace_sessions[0]=session;self.active_workspace_index=0
        else:
            self.workspace_sessions.append(session);self.active_workspace_index=len(self.workspace_sessions)-1
        self._rebuild_session_tabs();self._load_workspace(self.active_workspace_index);self._persist_workspace_quiet()
    def reload_logs(self):
        kind=self._active_workspace().get('type')
        if kind=='contest':self.reload_contest_logs();return
        if kind=='easy':self.reload_easy_logs();return
        if kind=='free':self.reload_free_logs();return
        if not self.station:return
        try:
            self.repo.recover()
            sessions={p:self.repo.open(p) for p in self.repo.files(self.station[0])}
            self.sessions=sessions
            self.rows=session_rows(sessions,self.station[0])
            issues=sum(len(s.log.issues) for s in sessions.values())
            self.status.setText(f'{len(self.rows)}交信を読み込みました。要確認行 {issues}件。')
            if issues:QMessageBox.warning(self,'ログの確認','解釈できない行のあるファイルは保存できません。audit.pyで行番号と理由を確認できます。')
            self.update_path();self.search()
        except (StorageError,OSError) as e:QMessageBox.warning(self,'読み込み',str(e))
    def closeEvent(self,event):
        # A full restore has already written the selected config/logbook state.
        # Do not let the still-running pre-restore UI write its old settings back.
        if getattr(self,'_full_restore_exit',False) or getattr(self,'_update_exit',False):
            event.accept();return
        try:
            errors=self.repo.close()
            if errors:raise StorageError('終了時バックアップに失敗しました。'+str(errors))
            self.persist_settings()
        except (StorageError,OSError,ValueError) as e:
            QMessageBox.warning(self,'終了前の保存',str(e));event.ignore();return
        event.accept()
    def _normalize_standard_field(self,key):
        try:
            value=self.text(key)
            if key=='date':value=date_text(value)
            elif key=='time':value=time_text(value)
            elif key in ('mode','code'):value=machine_text(value,upper=True)
            else:value=machine_text(value)
            self.set_text(key,value)
        except ValueError:
            # Keep an unrecognized value visible so Record can show the normal
            # field-specific validation message instead of interrupting Tab use.
            return False
        return True
    def _normalize_sub_mode(self):
        self.sub_mode.setCurrentText(machine_text(self.sub_mode.currentText(),upper=True))
    def _normalize_contest_line(self,widget,kind):
        try:
            value=widget.text()
            if kind=='date':value=date_text(value)
            elif kind=='time':value=time_text(value)
            else:value=machine_text(value)
            widget.setText(value)
        except ValueError:
            return False
        return True
    def text(self,key):
        if key=='mode':
            return combine_mode_value(self.fields['mode'].currentText(),self.sub_mode.currentText(),self.sub_mode_on.isChecked())
        e=self.fields[key]; return e.currentText() if isinstance(e,QComboBox) else e.text()
    def set_text(self,key,value):
        if key=='mode':
            main_mode,sub=split_mode_value(value)
            self.fields['mode'].setCurrentText(main_mode)
            self.sub_mode.setCurrentText(sub)
            self.sub_mode_on.setChecked(bool(sub))
            self.toggle_sub_mode(bool(sub))
            return
        e=self.fields[key]; e.setCurrentText(value) if isinstance(e,QComboBox) else e.setText(value)
    def toggle_sub_mode(self,on):
        self.sub_mode.setVisible(bool(on))
        if on:
            self.mode_editor_layout.setStretch(0,55);self.mode_editor_layout.setStretch(1,45)
        self.mode_changed(self.text('mode'))
    def mode_return_pressed(self):
        if self.sub_mode_on.isChecked():
            self.sub_mode.setFocus()
            if self.sub_mode.lineEdit():self.sub_mode.lineEdit().selectAll()
        else:
            self.fields['sent'].setFocus()
    def set_station(self):
        self._activate_station(True)
    def _activate_station(self,save_now):
        try:call=validate_station(self.own.text(),self.suffix.text())
        except ValueError as e:QMessageBox.warning(self,'自局設定',str(e));return False
        suffix=self.suffix.text()
        self.station=(call,suffix); self.own.setText(call); self.entry.setEnabled(True)
        if self._active_workspace().get('type') in ('standard','easy'):
            session=self._active_workspace()
            session.update(call=call,suffix=suffix,band=self.text('band'),mode=self.text('mode'),my_qth=self.text('my_qth'))
            self.session_tabs.setTabText(self.active_workspace_index,session_title(session))
        if save_now:
            try:self.persist_settings()
            except (ValueError,StorageError,OSError) as e:
                QMessageBox.warning(self,'自局設定の保存',str(e))
        self.reload_logs(); self.call.setFocus();return True
    def update_path(self):
        try:
            date=self.text('date') or now_jst().strftime('%Y-%m-%d')
            p=self.repo.path_for(*self.station,date)
            if p not in self.sessions:self.sessions[p]=self.repo.open(p)
            self.path.setText(str(p))
        except (ValueError,StorageError,OSError):self.path.setText('日付を正しく入力してください')
        self._update_current_log_buttons()
    def start_qso(self):
        if not self.call.text().strip():self.call.setFocus();return
        self.blacklist_ack=None
        self.call.setText(normalize_callsign(self.call.text())); n=now_jst()
        self.warn_blacklist(self.call.text())
        self.set_text('date',n.strftime('%Y-%m-%d'));self.set_text('time',n.strftime('%H:%M'))
        for key in ('his_qth','code','remarks'):self.set_text(key,'')
        self.rmks2.clear()
        if not self.keep_band.isChecked():self.set_text('band','')
        if not self.keep_mode.isChecked():self.set_text('mode','')
        if self.auto_rst.isChecked():self.mode_changed(self.text('mode'))
        country_note=''
        if self.location_on.isChecked():
            try:
                hint=self._country_hint(self.call.text())
                if hint:self.set_text('his_qth',hint['country']);country_note=' 国名は参照DBによる候補です。'
            except (StorageError,OSError) as e:country_note=' 国名補助: '+str(e)
        self.update_path();self.search();self.fields['date'].setFocus()
        self.status.setText(self.call.text()+' をセットしました。Enterで次の項目へ進みます。'+country_note)
    def mode_changed(self,mode):
        # During Window.__init__, the saved MODE/SUB value is restored before
        # the auto-RST checkbox itself is created.  Sub-mode UI changes may
        # therefore call this method during that early restore phase.
        if not hasattr(self,'auto_rst') or not self.auto_rst.isChecked():return
        value=default_rst(mode)
        for key in ('sent','received'):self.set_text(key,value or '')
    def search(self):
        if not self.station:return
        call=self.call.text().strip().upper()
        # Portable suffixes (/P, /1, /JD1, etc.) are the same station for
        # previous-QSO history.  Keep the entered callsign itself unchanged;
        # only the history lookup is grouped by the base callsign.
        base=call.split('/',1)[0] if call else ''
        def same_history_station(value):
            value=(value or '').strip().upper()
            return bool(base) and (value==base or value.startswith(base+'/'))
        candidates=[(owner,r) for owner,r in self.rows if same_history_station(r.call) and owner[0]==self.station[0] and (not self.limited.isChecked() or owner==self.station)]
        if self.limited.isChecked():candidates=[item for item in candidates if item[1].date[:4]==(self.text('date')[:4] or str(now_jst().year))]
        candidates.sort(key=lambda item:(item[1].date,item[1].time),reverse=True)

        # Keep the true total.  The old UI truncated to 30 before counting,
        # which made active stations look as if they had only 30 QSOs.
        visible=candidates[:20];self._standard_history_visible=visible
        self.table.setRowCount(len(visible))
        for i,(_owner,r) in enumerate(visible):
            values=[r.call,r.date+' '+r.time,r.band,r.mode,r.sent+' / '+r.received,r.his_qth,r.code,'QSLR' if r.confirmed else '—']
            for j,v in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(v))
        self.summary.setText(self._history_summary_html(base,len(candidates)) if call else self._history_summary_html('',0))
        self.more.setText('他 '+str(len(candidates)-len(visible))+'件' if len(candidates)>len(visible) else '読み込んだTXTの交信を表示しています')
    def _history_hit(self,owner,qso):
        return embedded_history_hit(self.sessions,owner,qso)
    def _show_embedded_history_detail(self,row,visible,reload_callback):
        if row<0 or row>=len(visible):return
        owner,qso=visible[row];hit=self._history_hit(owner,qso)
        if hit is None:
            QMessageBox.warning(self,'交信詳細','対象の交信を現在のログから特定できませんでした。ログを再読み込みしてください。');return
        from search_ui import DetailDialog
        dialog=DetailDialog(self.repo,hit,self);dialog.exec()
        if dialog.saved:reload_callback()
    def show_standard_history_detail(self,row=None):
        if row is None:row=self.table.currentRow()
        self._show_embedded_history_detail(row,getattr(self,'_standard_history_visible',[]),self.reload_logs)
    def show_contest_history_detail(self,row=None):
        if row is None:row=self.c_table.currentRow()
        self._show_embedded_history_detail(row,getattr(self,'_contest_history_visible',[]),self.reload_contest_logs)

    def _apply_rmks2_visibility(self,on):
        self.rmks2_label.setVisible(bool(on));self.rmks2.setVisible(bool(on))
    def rmks2_visibility_changed(self,on):
        if not on and self.rmks2.text():
            answer=QMessageBox.question(self,'RMKS2を非表示','RMKS2の入力内容を消して非表示にしますか？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:
                self.rmks2_toggle.blockSignals(True);self.rmks2_toggle.setChecked(True);self.rmks2_toggle.blockSignals(False);self._apply_rmks2_visibility(True);return
            self.rmks2.clear()
        self._apply_rmks2_visibility(on)
        if not self._workspace_loading and self._active_workspace().get('type') in ('standard','easy'):
            self._active_workspace()['rmks2_visible']=bool(on);self._persist_workspace_quiet()
    def remarks_return_pressed(self):
        if self.rmks2_toggle.isChecked():self.rmks2.setFocus()
        else:self.record()

    def location(self,target='his_qth'):
        from location_ui import LocationDialog
        try:dialog=LocationDialog(self.data_root,self.text('code') if target=='his_qth' else '',self,remember_default=(target=='my_qth'))
        except (StorageError,OSError,ValueError) as e:QMessageBox.warning(self,'所在地DB',str(e));return
        if dialog.exec()!=QDialog.DialogCode.Accepted or not dialog.result_value:return
        qth,code=dialog.result_value;old=self.text(target);new=preserve_grid(old,qth)
        if old and old!=new and QMessageBox.question(self,'所在地の反映','既存の所在地を置き換えますか？\nGLは保持します。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.set_text(target,new)
        if target=='his_qth':self.set_text('code',code)
    def record(self):
        try:
            values={k:self.text(k) for k in self.fields};validate_remarks_component(values['remarks'],'RMKS');validate_remarks_component(self.rmks2.text(),'RMKS2')
            values['remarks']=compose_remarks(values['remarks'],self.rmks2.text() if self.rmks2_toggle.isChecked() else '')
            values['call']=normalize_callsign(self.call.text());q=QSO(**values);q.validate()
            self.call.setText(q.call)
            for key in ('date','time','band','mode','sent','received','code'):self.set_text(key,getattr(q,key))
        except ValueError as e:
            QMessageBox.warning(self,'入力確認',str(e))
            from input_feedback import focus_error
            focus_error(e,dict(self.fields,call=self.call));return
        self.warn_blacklist(q.call)
        time_choice=self._confirm_record_time(q)
        if time_choice=='cancel':
            self.status.setText('現在時刻との差を確認するため記録を中止しました。')
            self.fields['time'].setFocus();self.fields['time'].selectAll();return
        if time_choice=='current':
            self.set_text('date',q.date);self.set_text('time',q.time);self.update_path()
        if time_choice=='normal' and self.settings['confirm_record'] and QMessageBox.question(self,'記録確認',q.date+' '+q.time+' JST　'+q.call+'\nTXTログへ記録しますか？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)!=QMessageBox.StandardButton.Yes:return
        try:
            if not self.station: raise StorageError('自局をSETしてください。')
            path=self.repo.path_for(*self.station,q.date)
            session=self.sessions.get(path) or self.repo.open(path)
            session.append(q);self.sessions[path]=session
        except (StorageError,OSError) as e:QMessageBox.warning(self,'保存できません',str(e));return
        settings_error=''
        try:self.persist_settings()
        except (StorageError,OSError,ValueError) as e:
            settings_error=' ／ 交信は保存済みですが、最新入力値の保存に失敗しました: '+str(e)
        self.rows=session_rows(self.sessions,self.station[0])
        self.status.setText(q.call+' を保存しました：'+str(path)+settings_error)
        self.search();self.call.clear();self.set_text('his_qth','');self.set_text('code','');self.call.setFocus()

def update_self_check():
    """Lightweight frozen-build probe used before an update is committed."""
    try:
        import update_launcher  # noqa: F401 - force PyInstaller archive read
        import update_package   # noqa: F401 - shared update validator
    except Exception:
        return 91
    return 0



def _update_launch_token(argv):
    try:
        i=argv.index('--update-launch-token')
        return argv[i+1] if i+1<len(argv) else ''
    except ValueError:
        return ''


def _wait_for_update_if_needed(app,data_root,launch_token=''):
    """Block accidental manual starts while PSLogUpdater owns the update."""
    try:
        from update_state import lock_status
        status,data=lock_status(data_root)
    except Exception:
        return True,''
    if status!='active' or not data:
        return True,''
    if launch_token and data.get('token')==launch_token:
        return True,str(launch_token)

    dialog=QDialog();dialog.setWindowTitle('PSLog バージョンアップ待ち');dialog.setModal(True);dialog.resize(470,150)
    layout=QVBoxLayout(dialog)
    label=QLabel('PSLogのバージョンアップ処理が完了待ちです。\n更新画面から起動するか、約10秒そのままお待ちください。')
    label.setWordWrap(True);layout.addWidget(label)
    timer=QTimer(dialog)
    def poll():
        try:now,_=lock_status(data_root)
        except Exception:now='none'
        if now!='active':dialog.accept()
    timer.timeout.connect(poll);timer.start(200);dialog.exec();timer.stop()
    # This process was started manually while an updater owned the gate.  Once
    # the gate disappears (normal completion or updater failure), close this
    # warning process instead of racing the updater's official PSLog launch.
    # If the updater died, a fresh manual start will see the stale lock removed.
    return False,''

def launch():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setFont(QFont('Yu Gothic UI',10))
    icon_path=app_resource('assets/pslog_icon.png')
    if icon_path.is_file():app.setWindowIcon(QIcon(str(icon_path)))
    root=data_directory()
    token=_update_launch_token(sys.argv)
    proceed,official_token=_wait_for_update_if_needed(app,root,token)
    if not proceed:return 0
    try:
        guard=SingleInstanceGuard()
    except OSError as e:
        QMessageBox.critical(None,'PSLogを起動できません',str(e))
        return 1
    if guard.already_running:
        QMessageBox.information(None,'PSLogは起動済み','PSLogはすでに起動しています。\n二重起動はできません。')
        return 0
    try:
        try:w=Window(root,reset_window='--reset-window' in sys.argv)
        except (OSError,StorageError,ValueError) as e:
            QMessageBox.critical(None,'PSLogを起動できません',
                f'データの場所: {root}\n\n{e}\n\n設定ファイルと保存先のアクセス権を確認してください。\n設定やログを自動初期化せず、起動を中止しました。')
            return 1
        # The updater-launched process owns the one-time token.  Release the
        # startup gate only after the new Window was constructed successfully;
        # waiting accidental starts then close automatically.
        if official_token:
            try:
                from update_state import remove_lock
                remove_lock(root,official_token)
            except Exception:pass
        try:
            from update_state import cleanup_stale_rollbacks
            cleanup_stale_rollbacks(root)
        except Exception:pass
        w.show();QTimer.singleShot(0,w.monthly_backup_notice);code=app.exec()
        return RESTART_EXIT_CODE if getattr(w,'_restart_requested',False) else code
    finally:
        guard.release()

def _restart_command():
    if getattr(sys,'frozen',False):return [sys.executable]
    return [sys.executable,str(Path(__file__).resolve())]

if __name__=='__main__':
    if '--update-self-check' in sys.argv:
        sys.exit(update_self_check())
    code=launch()
    if code==RESTART_EXIT_CODE:
        try:subprocess.Popen(_restart_command(),cwd=str(data_directory()),close_fds=True)
        except OSError as e:
            print('PSLogを再起動できません:',e,file=sys.stderr);sys.exit(1)
        sys.exit(0)
    sys.exit(code)
