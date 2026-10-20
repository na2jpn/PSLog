"""Application-volume notification audio; no system beep fallback."""
from pathlib import Path
from PySide6.QtCore import QObject,QUrl,QTimer
SOUNDS=(('standard','標準'),('terere','テレレレッテレー'))
class AlertPlayer(QObject):
    def __init__(self,parent=None):
        super().__init__(parent);self.effect=None;self.pending=[];self.active=False;self.started=False
    def play(self,volume=50,sound='standard'):
        if volume<=0:return
        if self.effect is None:
            from PySide6.QtMultimedia import QSoundEffect
            self.effect=QSoundEffect(self);self.effect.setLoopCount(1)
            self.effect.playingChanged.connect(self._changed)
            self.effect.statusChanged.connect(self._status)
        self.pending.append((volume,sound));self._next()
    def _next(self):
        if self.active or not self.pending:return
        volume,sound=self.pending.pop(0);self.active=True;self.started=False
        self.effect.setVolume(volume/100)
        self.effect.setSource(QUrl.fromLocalFile(str(Path(__file__).resolve().parent/'assets/sounds'/('terere.wav' if sound=='terere' else 'standard.wav'))))
        self.effect.play()
    def _changed(self):
        if self.effect.isPlaying():self.started=True
        elif self.active and self.started:
            self.active=False;QTimer.singleShot(0,self._next)
    def _status(self):
        from PySide6.QtMultimedia import QSoundEffect
        if self.effect.status()==QSoundEffect.Status.Error:
            self.stop()
    def stop(self):
        self.pending.clear();self.active=False;self.started=False
        if self.effect is not None:self.effect.stop()
