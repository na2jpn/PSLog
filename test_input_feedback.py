import unittest
from dataclasses import replace
from model import QSO,InputError
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLineEdit
from input_feedback import focus_error

class InputFeedbackTests(unittest.TestCase):
    def test_identifies_exact_field_and_normalizes_fullwidth_dates(self):
        q=QSO('2026-09-11','12:00','7','CW','JA1AAA','599','599','','','')
        for field,value in [('date','2026-02-30'),('date','26/9/11'),('time','24:00'),('time','12:99'),('sent','59'),('received','59'),('remarks','bad|note')]:
            with self.assertRaises(InputError) as e:replace(q,**{field:value}).validate()
            self.assertEqual(e.exception.field,field)
        wide=replace(q,date='２０２６-０９-１１',time='１２:００');wide.validate();self.assertEqual(wide.date,q.date);self.assertEqual(wide.time,q.time)
        replace(q,mode='FUTURE',sent='arbitrary',received='value').validate()
    def test_field_focus_and_selection(self):
        app=QApplication.instance() or QApplication([]);window=QWidget();layout=QVBoxLayout(window)
        fields={key:QLineEdit('invalid') for key in ('date','time')}
        for w in fields.values():layout.addWidget(w)
        window.show();app.processEvents();focus_error(InputError('time','bad'),fields)
        self.assertEqual(window.focusWidget(),fields['time']);self.assertEqual(fields['time'].selectedText(),'invalid')
        window.close();window.deleteLater()
