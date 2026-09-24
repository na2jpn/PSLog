"""Manual synthetic 10,000-QSO check; temporary files only."""
import tempfile,time,csv,io
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from storage import Repository,ExternalChange
from model import QSO
from contest import select_logs,entries
from contest_rules import default_rule,score
from contest_export import plan,save,key
from contest_score_ui import ScoreView
from contest_task_ui import run_task

def main():
    app=QApplication.instance() or QApplication([]);ticks=[]
    timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(time.perf_counter()));timer.start()
    with tempfile.TemporaryDirectory() as folder:
        repo=Repository(folder);path=repo.path_for('JH1HST','','2026-09-12')
        path.parent.mkdir(parents=True,exist_ok=True)
        data=('\ufeff'+'\r\n'.join(QSO('2026-09-12','12:00','7','CW',f'JA1A{i}','599','599','Japan','Soka Saitama Japan','001A').to_ps() for i in range(10000))+'\r\n').encode('utf-8');path.write_bytes(data)
        started=time.perf_counter();selection=run_task(None,'10000件読込',lambda:select_logs(repo,[path],'JH1HST'));loaded=time.perf_counter()
        rule=default_rule();draft={key(r):{'sent':'11M','received':'001A'} for r in selection.rows}
        result=run_task(None,'採点',lambda:score(rule,entries(selection,draft)))
        view=ScoreView();view.set_result(selection,result,draft);view.move(99)
        assert view.table.rowCount()==100 and view.table.item(99,0).text()=='10000'
        prepared=run_task(None,'出力準備',lambda:plan(selection,rule,draft,'zLog令和版CSV',{'zone':'JST','memo':True,'power_code':'L'}))
        output=run_task(None,'保存',lambda:save(prepared,folder));finished=time.perf_counter()
        rows=list(csv.reader(io.StringIO(output.read_text('utf-8-sig'))));assert len(rows)==10001 and all(len(r)==34 for r in rows)
        assert path.read_bytes()==data and ticks
        path.write_bytes(data+b'\r\n')
        try:run_task(None,'変更検出',lambda:save(prepared,folder))
        except ExternalChange:pass
        else:raise AssertionError('external change was not detected')
        print(f'10000 QSO: load={loaded-started:.3f}s total={finished-started:.3f}s GUI timer={len(ticks)}; 34 columns/all rows/original preserved/external change blocked: OK')
        view.deleteLater()
    timer.stop()
if __name__=='__main__':main()
