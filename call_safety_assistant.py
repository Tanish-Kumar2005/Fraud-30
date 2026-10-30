from typing import Dict, Optional
from voice_clone_detector import VoiceCloneDetector
from scam_script_detector import ScamScriptDetector
from warning_display import WarningDisplay


class CallSafetyAssistant:

    def __init__(self, v_thr=0.65, s_thr=0.5, del_after=False, sr=16000):
    
        self.vd = VoiceCloneDetector(sr=sr, thr=v_thr)
        self.sd = ScamScriptDetector(thr=s_thr)
        self.wd = WarningDisplay()
        self.del_after = del_after
        self.sr = sr

    def analyse_call(self, path, transcript=None, delete_audio=None):
    
        da = self.del_after if delete_audio is None else delete_audio
        v = self.vd.detect_from_file(path, delete_after=da)
        sc = self.sd.detect(transcript) if transcript else None
        ws = self.wd.process_both(v, sc or {"is_scam": False, "risk_score": 0.0})
        risk = self._risk(v, sc)
    
        return {"voice_clone": v, "scam_script": sc, "combined_risk": risk, "warnings": [{"timestamp": w.timestamp, "type": w.warning_type, "severity": w.severity, "message": w.message, "acknowledged": w.acknowledged} for w in ws], "recommendation": self._rec(risk, v, sc), "summary": self._summ(v, sc, risk), "audio_deleted": da, "source_file": path}

    def analyse_audio(self, a, sr=None, transcript=None):
    
        sr = sr or self.sr
        v = self.vd.detect_from_audio(a, sr)
        sc = self.sd.detect(transcript) if transcript else None
        ws = self.wd.process_both(v, sc or {"is_scam": False, "risk_score": 0.0})
        risk = self._risk(v, sc)
    
        return {"voice_clone": v, "scam_script": sc, "combined_risk": risk,
                "warnings": [{"timestamp": w.timestamp, "type": w.warning_type,
                              "severity": w.severity, "message": w.message,
                              "acknowledged": w.acknowledged} for w in ws],
                "recommendation": self._rec(risk, v, sc),
                "summary": self._summ(v, sc, risk), "audio_deleted": False,
                "source_file": None}

    def _risk(self, v, sc):
    
        vs = v.get("is_synthetic", False); vp = v.get("synthetic_probability", 0)
        ss = sc.get("is_scam", False) if sc else False; sp = sc.get("risk_score", 0) if sc else 0
        if vs and ss: return "critical"
        if vs and vp >= 0.8: return "critical"
        if ss and sp >= 0.8: return "critical"
        if vs or ss: return "warning"
        if vp >= 0.5 or (sc and sp >= 0.3): return "caution"
    
        return "safe"

    def _rec(self, risk, v, sc):
    
        if risk == "critical": return "🚨 CRITICAL: Fraud likely. Do NOT transfer money. Hang up and verify with family."
        if risk == "warning": return "⚠️ WARNING: Suspicious indicators. Verify caller identity with family first."
        if risk == "caution": return "⚠️ CAUTION: Minor concerns. Verify claims independently before sharing info."
    
        return "✓ SAFE: No significant fraud indicators detected."

    def _summ(self, v, sc, risk):
    
        vp = v.get("synthetic_probability", 0); vs = v.get("is_synthetic", False)
        p = [f"Voice: {'SYNTHETIC' if vs else 'Natural'} (p={vp:.2f})"]
    
        if sc:
    
            sd_ = sc.get("is_scam", False); sp = sc.get("risk_score", 0)
            p.append(f"Scam: {'SCAM' if sd_ else 'Clean'} (r={sp:.2f})")
    
        else: 
            
            p.append("Scam: N/A (no transcript)")
    
        p.append(f"Risk: {risk.upper()}")
        return " | ".join(p)

    def warn_summary(self): 
        
        return self.wd.summary()
    
    def ack(self, i): 
        
        return self.wd.ack(i)
    
    def clear(self): 
        
        self.wd.clear()


def analyse_call(path, transcript=None, v_thr=0.65, s_thr=0.5, delete_audio=False):
    
    a = CallSafetyAssistant(v_thr, s_thr, delete_audio)
    return a.analyse_call(path, transcript, delete_audio)