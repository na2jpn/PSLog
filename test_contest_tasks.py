import threading,unittest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from contest_task_ui import run_task,TaskDialog

class ContestTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_gui_events_continue_and_escape_cannot_detach_worker(self):
        released=threading.Event();worker_ids=[];main_id=threading.get_ident();ticks=[]
        timer=QTimer();timer.setInterval(5)
        def tick():
            ticks.append(True)
            for w in self.app.topLevelWidgets():
                if isinstance(w,TaskDialog):w.reject();self.assertTrue(w.isVisible())
            released.set()
        timer.timeout.connect(tick);timer.start()
        def work():
            worker_ids.append(threading.get_ident())
            if not released.wait(2):raise RuntimeError('GUI timer did not run')
            return 42
        try:self.assertEqual(run_task(None,'テスト',work),42)
        finally:timer.stop()
        self.assertTrue(ticks);self.assertNotEqual(worker_ids[0],main_id)
    def test_errors_reach_caller_and_next_operation_still_works(self):
        def fail():raise ValueError('外部変更のテスト')
        with self.assertRaisesRegex(ValueError,'外部変更'):run_task(None,'テスト',fail)
        self.assertEqual(run_task(None,'テスト',lambda:'OK'),'OK')
