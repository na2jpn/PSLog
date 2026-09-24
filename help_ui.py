import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout,QPlainTextEdit,QWidget,QLabel,QScrollArea,QGroupBox,QFrame
from window_geometry import SafeDialog
from search_ui import button
from storage import VERSION

TEXTS={
'使い方':f'''PSLog {VERSION} — 基本操作

1. 自局コールサインと必要ならログ付与文字を入力し、SETします。
2. 相手コールを入力してEnter。日時がJSTで入り、新しい交信入力を始めます。
3. BAND、MODE、送受RST、所在地などを確認して記録します。
   日時は手直しできます。MY QTHはその交信時の運用場所を記入してください。

右側LogSearchは現在の自局表記を完全一致で検索します。
/1等を含めて横断検索したい場合は「編集 → ログ検索・編集」を使用してください。
検索結果から編集・削除できます。DATEの年変更では移動先を確認します。

所在地補助はON/OFF可能。国名候補は交信当時の運用地を確認してください。
長い原本パスは途中を省略し、マウスを置くと全文表示、右クリックで全文コピーできます。

「入出力」から通常の取り込み・出力、POTA/SOTAの特殊出力を開きます。
インポートの標準は重複無視。全追加は同じ交信も追加する指定です。
コンテストは形式 → 対象ログ → ナンバー → 採点 → 提出情報・出力の順です。
作業ナンバー等は原本に書き戻しません。ルールは参照年と規約を確認してください。

QSL受領一括では受領方法を毎回明示選択し、日付・コール・時刻±5分で照合します。
一意一致だけを自動選択し、複数候補・未一致は詳細画面で確認します。
BURO判定は BURO=発送済、BURO.R=発送/受領済です。送付済みタグは受領時に .R 付きへ昇格します。
結果のMY QTHは現在値ではなく、その交信の記録です。

途中保存で止まったら、同じ一括操作を再実行せず「ファイル → ログを再読込」で回復します。
外部変更があれば上書きを止めます。表示された原本・結果・回復記録を保全してください。
旧形式の中断記録や競合の自動解決は対象外です。

バックアップから復元するときは、置換前の現行ログも保護します。
「今すぐバックアップ」はconfig/logbookの全体ZIP作成です。
全体ZIP専用復元はまだありません。個別ログ復元と区別してください。
''',
'PSLogフォーマットについて':'''PSLogフォーマットについて

PS = Pipe Separate（パイプセパレート）。
各項目をパイプ記号 | で区切ることから、この名称を使用しています。

PSLogのログデータは、専用データベースではなくテキストファイル（TXT）として保存します。
1交信を1行で記録し、正式原本は logbook フォルダー内のTXTです。
文字コードはUTF-8で、新規作成ファイルはBOM付き・CRLFで保存します。
テキストエディタでも内容を確認できますが、通常の編集はPSLog上で行うことを推奨します。

PSLog TXT — 11項目固定

DATE | TIME | BAND | MODE | HIS CALLSIGN | RSTs | RSTr | HIS QTH | MY QTH | RMKS | JCCJCG

1行1交信。各項目を「半角スペース | 半角スペース」で区切り、
末尾には半角スペースとバックスラッシュ2文字を付けます。

DATE: YYYY-MM-DD
TIME: hh:mm JST（JST・分精度）
BAND: MHz基準の代表値。実際の交信周波数とは別です。
JCCJCG: 相手の番号。任意で、空欄でも区切りを省略しません。
MY QTHの補助番号をJCCJCGへ入れません。

新規ファイル: UTF-8 BOM付き、CRLF。
既存読込: BOMあり/なし、従来10項目にも対応。
未編集行の表記や既存改行を保持します。問題行は黙って補修せず通知します。
項目内の |、改行、タブは使用できません。

正式原本はlogbook配下のTXTです。
年_自局コール_付与文字.txt（自局の / はファイル名では -）。
保存する年は交信DATEの年。RMKSの自由メモやQSL表記を勝手に分割して列追加しません。
RMKS2を使用する場合も列数は増やさず、RMKS欄を「RMKS1 <<RMKS2>> RMKS2」の形式で保存します。
<<RMKS2>> はPSLogの構造用予約文字列です。RMKS2がない交信は従来どおりRMKS1だけを保存します。
''',

'起動コマンドフラグについて':'''起動コマンドフラグについて

PSLogは起動時にコマンドラインフラグを指定できます。

--reset-window
保存されているウィンドウ位置・サイズ・最大化状態を無視し、初期状態で起動します。

・基準サイズは1360×850です。
・画面が狭い場合は、利用可能な画面内に収まるよう自動調整します。
・最大化状態は解除します。
・保存位置が画面外にある場合も、現在の画面内へ戻します。
・この状態で通常終了すると、その時点のウィンドウ位置・サイズが新しく保存されます。

使用例
PSLog.exe --reset-window

ウィンドウが画面外へ移動した場合や、保存された位置・サイズを初期化したい場合に使用してください。
''',
'PSLogについて':f'''PSLog {VERSION}

アマチュア無線交信ログソフト。Python / PySide6で動作します。

PS = Pipe Separate（パイプセパレート）
PSログフォーマットは、1交信を1行とし、各項目をパイプ記号 | で区切って保存するテキスト形式です。
正式原本はlogbookフォルダー内のPSログTXTです。

コンテスト提出では、大会の規定に応じてJARL電子ログ形式やCabrillo形式などを出力できます。
通常ログからADIF、Hamlog CSV、zLog CSV等への入出力にも対応します。

参照データには利用者提供のJCC/JCG資料、JARL登録クラブ資料、
Jim Reisert AD1CのAmateur Radio Country Filesを使用しています。
CTYの版・出典・配布条件はconfig/db/cty_meta.jsonとcty_LICENSE.txtに記載。
更新日時点の参照情報であり、過去の運用やアワードの有効性は別途確認が必要です。
'''}
from user_guide import GUIDE
TEXTS['使い方']=GUIDE.replace('PSLog 1.05 操作案内',f'PSLog {VERSION} 操作案内',1)
TEXTS['PSLogについて'] += '\n作者からの案内\nPSLogは、H.Tanakaが自身のアマチュア無線交信ログを管理するために私的に開発し、利用するソフトウェアです。\n作者自身の使いやすさを優先しており、第三者の要望への対応、サポート、不具合修正や継続提供を約束するものではありません。\n利用・改良は利用条件の範囲で自由ですが、利用者自身の判断と責任で行ってください。記録内容や提出ファイルの確認、必要なバックアップは利用者が行ってください。\n\nPSLog\nCopyright (c) 2026 H.Tanaka (JH1HST)\nOriginally developed by H.Tanaka (JH1HST)\nAKIHABARA-GIKEN\n\nBased on PSLog Format — established in 2013\n\n再配布について\n無改変版の再配布は認めていません。作者の配布元を案内してください。\n改良版を再配布する場合は、元となるPSLogの版、変更箇所・変更内容、改良版の名称と版、配布責任者を明示してください。\nまた、対応する改良版のソースコード全体と、ビルドに必要なスクリプト・設定を受領者が取得できるようにしてください。\n改良版の配布前に、作者へ改良内容、配布先、配布者本人の氏名と連絡先を通知してください。作者の個別承認を条件とするものではありません。\n元作者の表示を保持し、作者の公式版または作者が保証する版であると誤認させないでください。\nPython、PySide6/Qt、PyInstaller、CTY等の第三者のライブラリ・素材・参照データには、それぞれの利用条件が適用されます。'

def _resource(relative):
    return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/relative


def _section(title,text,parent):
    box=QGroupBox(title,parent);layout=QVBoxLayout(box);label=QLabel(text,box);label.setWordWrap(True);label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setStyleSheet('font-size:14px; line-height:1.3;');layout.addWidget(label);return box


class HelpDialog(SafeDialog):
    def __init__(self,topic,parent=None):
        super().__init__(parent);self.setWindowTitle(topic+f' — PSLog {VERSION}')
        if topic=='PSLogについて':
            self._build_about();return
        self.resize(780,600);v=QVBoxLayout(self);text=QPlainTextEdit();text.setReadOnly(True);text.setPlainText(TEXTS[topic]);v.addWidget(text,1);v.addWidget(button('閉じる',self.accept))

    def _build_about(self):
        self.resize(760,720);outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame)
        body=QWidget();v=QVBoxLayout(body);v.setContentsMargins(18,16,18,16);v.setSpacing(12)
        icon=QLabel();icon.setAlignment(Qt.AlignmentFlag.AlignCenter);path=_resource('assets/pslog_icon.png')
        if path.is_file():
            pix=QPixmap(str(path));icon.setPixmap(pix.scaled(96,96,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        v.addWidget(icon)
        title=QLabel(f'PSLog {VERSION}');title.setAlignment(Qt.AlignmentFlag.AlignCenter);title.setStyleSheet('font-size:25px; font-weight:700; color:#285b37;');v.addWidget(title)
        sub=QLabel('アマチュア無線交信ログソフト');sub.setAlignment(Qt.AlignmentFlag.AlignCenter);sub.setStyleSheet('font-size:15px; color:#53606a;');v.addWidget(sub)
        v.addWidget(_section('PSLog / PSログフォーマット',
            'PS は Pipe Separate（パイプセパレート）の略です。\n'
            'PSログフォーマットは、1交信を1行とし、各項目をパイプ記号「|」で区切って保存するテキスト形式です。\n'
            '正式原本は logbook フォルダー内のPSログTXTです。',body))
        v.addWidget(_section('主な機能',
            '通常交信ログ、EASY入力、コンテスト、QSOパーティ、アワード、QSL受領処理を1つのログ原本で扱います。\n'
            'コンテスト提出は大会規定に応じてJARL電子ログ形式やCabrillo形式などへ出力できます。\n'
            'ADIF、Hamlog CSV、zLog CSV等の入出力にも対応します。',body))
        v.addWidget(_section('参照データ',
            '利用者提供のJCC/JCG資料、JARL登録クラブ資料、Jim Reisert AD1CのAmateur Radio Country Filesを参照しています。\n'
            'CTYの版・出典・配布条件は config/db/cty_meta.json と cty_LICENSE.txt に記載しています。\n'
            '更新日時点の参照情報であり、過去の運用やアワードの有効性は別途確認が必要です。',body))
        author='H.Tanakaが自身のアマチュア無線交信ログを管理するために開発したソフトウェアです。\n'
        author+='記録内容や提出ファイルの確認、必要なバックアップは利用者自身で行ってください。\n\n'
        author+='Copyright (c) 2026 H.Tanaka (JH1HST)\nAKIHABARA-GIKEN\nBased on PSLog Format — established in 2013'
        v.addWidget(_section('作者からの案内',author,body));v.addStretch(1);scroll.setWidget(body);outer.addWidget(scroll,1);outer.addWidget(button('閉じる',self.accept))
