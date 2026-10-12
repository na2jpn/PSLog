import unittest
from types import SimpleNamespace

from radio_control import _open_serial_safe, _rigctld_command


class FakeSerialPort:
    def __init__(self):
        self.events=[]
        self.is_open=False
        self._dtr=None
        self._rts=None
        self.port=None
        self.baudrate=None
        self.timeout=None
        self.write_timeout=None
        self.rtscts=None
        self.dsrdtr=None
        self.xonxoff=None

    @property
    def dtr(self):
        return self._dtr

    @dtr.setter
    def dtr(self, value):
        self._dtr=bool(value)
        self.events.append(('dtr',bool(value),self.is_open))

    @property
    def rts(self):
        return self._rts

    @rts.setter
    def rts(self, value):
        self._rts=bool(value)
        self.events.append(('rts',bool(value),self.is_open))

    def open(self):
        self.events.append(('open',self._dtr,self._rts))
        self.is_open=True

    def close(self):
        self.events.append(('close',))
        self.is_open=False


class FakeSerialModule:
    def __init__(self):
        self.instance=None

    def Serial(self):
        self.instance=FakeSerialPort()
        return self.instance


class RadioSafetyFix2Tests(unittest.TestCase):
    def test_dtr_rts_are_off_before_serial_open(self):
        serial=FakeSerialModule()
        obj=_open_serial_safe(serial,'COM8',115200,timeout=.03,write_timeout=.5)
        self.assertIs(obj,serial.instance)
        self.assertEqual(obj.port,'COM8')
        self.assertEqual(obj.baudrate,115200)
        self.assertFalse(obj.rtscts)
        self.assertFalse(obj.dsrdtr)
        open_event=next(e for e in obj.events if e[0]=='open')
        self.assertEqual(open_event,('open',False,False))
        before_open=obj.events[:obj.events.index(open_event)]
        self.assertIn(('dtr',False,False),before_open)
        self.assertIn(('rts',False,False),before_open)
        self.assertFalse(obj.dtr)
        self.assertFalse(obj.rts)

    def test_rigctld_disables_ptt_and_modem_ptt_lines(self):
        command=_rigctld_command('rigctld.exe',1035,'COM9',38400,4532)
        self.assertIn('-P',command)
        self.assertEqual(command[command.index('-P')+1],'NONE')
        self.assertIn('-C',command)
        conf=command[command.index('-C')+1]
        self.assertIn('dtr_state=OFF',conf)
        self.assertIn('rts_state=OFF',conf)


if __name__=='__main__':
    unittest.main()
