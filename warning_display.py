import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False


@dataclass
class CallWarning:
    timestamp: str
    warning_type: str
    severity: str
    message: str
    details: Dict
    acknowledged: bool = False


class VoiceWarningHelper:
    def __init__(self):
        self.engine = None

    def speak(self, text: str):
        if not _TTS_AVAILABLE:
            return
        if self.engine is None:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)
                self.engine.setProperty('volume', 1.0)
            except Exception:
                return
        def _say():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                pass
        thread = threading.Thread(target=_say, daemon=True)
        thread.start()
class WarningDisplay:
    def __init__(self, enable_voice=True):
        self.active_warnings = []
        self.verify_prompt = False
        self._lock = threading.Lock()
        self.voice_helper = VoiceWarningHelper() if enable_voice else None

    def add(self, warning_type, severity, message, details=None):
        warning = CallWarning(
            timestamp=datetime.now().strftime('%H:%M:%S'),
            warning_type=warning_type,
            severity=severity,
            message=message,
            details=details or {},
        )
        with self._lock:
            self.active_warnings.append(warning)
        self._print_screen(warning)
        if severity in ('high', 'critical') and self.voice_helper:
            self.voice_helper.speak('Fraud detected. ' + message + '. End the call immediately.')
        return warning

    def process_voice(self, voice_result):
        if not voice_result.get('is_synthetic'):
            return None
        probability = voice_result.get('synthetic_probability', 0)
        confidence = voice_result.get('confidence', 'low')
        if confidence == 'high':
            severity = 'critical'
        elif confidence == 'medium':
            severity = 'high'
        else:
            severity = 'medium'
        message = f'Synthetic voice detected (probability: {probability:.2f}). The caller voice may be AI-cloned.'
        return self.add('voice_clone', severity, message, voice_result)

    def process_scam(self, scam_result):
        warnings = []
        if scam_result.get('is_scam'):
            risk_score = scam_result.get('risk_score', 0)
            summary = scam_result.get('summary', '')
            if risk_score >= 0.8:
                severity = 'critical'
            elif risk_score >= 0.6:
                severity = 'high'
            else:
                severity = 'medium'
            message = f'Scam pressure tactics detected: {summary}'
            warning = self.add('scam_script', severity, message, scam_result)
            warnings.append(warning)
        return warnings

    def process_both(self, voice_result, scam_result):
        warnings_added = []
        vw = self.process_voice(voice_result)
        if vw:
            warnings_added.append(vw)
        sw = self.process_scam(scam_result)
        warnings_added.extend(sw)
        if voice_result.get('is_synthetic') and scam_result.get('is_scam'):
            combined = self.add('combined', 'critical',
                'COMBINED THREAT: Synthetic voice AND scam tactics. This call is highly likely fraudulent.')
            warnings_added.append(combined)
        return warnings_added

    def _print_screen(self, warning):
        if warning.severity == 'critical':
            symbol = '***'
        elif warning.severity == 'high':
            symbol = '>>>'
        elif warning.severity == 'medium':
            symbol = '###'
        else:
            symbol = '...'
        print()
        print(symbol + ' [' + warning.timestamp + '] ' + warning.warning_type.upper() + ' (' + warning.severity.upper() + '): ' + warning.message)
        if warning.severity in ('high', 'critical') and not self.verify_prompt:
            self.verify_prompt = True
            print('============================================================')
            print('[!] VERIFY WITH FAMILY  -  This call may be fraudulent.')
            print('[!] Verify caller identity with family before sharing any info.')
            print('============================================================')

    def summary(self):
        with self._lock:
            warnings = list(self.active_warnings)
        if not warnings:
            return 'No warnings this call.'
        lines = ['=' * 60, 'CALL SAFETY SUMMARY', '=' * 60]
        for i, w in enumerate(warnings):
            ack = 'x' if w.acknowledged else ' '
            lines.append(f'[{ack}] {i+1}. [{w.timestamp}] {w.warning_type} | {w.severity.upper()} | {w.message}')
        lines.append('=' * 60)
        return '\n'.join(lines)

    def get_active_warnings(self):
        with self._lock:
            return [w for w in self.active_warnings if not w.acknowledged]

    def acknowledge(self, index):
        with self._lock:
            if 0 <= index < len(self.active_warnings):
                self.active_warnings[index].acknowledged = True
                return True
        return False

    def has_critical_warning(self):
        with self._lock:
            return any(not w.acknowledged and w.severity == 'critical' for w in self.active_warnings)

    def clear(self):
        with self._lock:
            self.active_warnings.clear()
        self.verify_prompt = False

    def get_active_warnings(self):
        with self._lock:
            return [w for w in self.active_warnings if not w.acknowledged]

    def acknowledge(self, index):
        with self._lock:
            if 0 <= index < len(self.active_warnings):
                self.active_warnings[index].acknowledged = True
                return True
        return False

    def has_critical_warning(self):
        with self._lock:
            return any(not w.acknowledged and w.severity == 'critical' for w in self.active_warnings)

    def clear(self):
        with self._lock:
            self.active_warnings.clear()
        self.verify_prompt = False
