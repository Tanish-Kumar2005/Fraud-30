import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

@dataclass
class ScamTactic:
    name: str
    category: str
    confidence: float
    matches: List[str] = field(default_factory=list)
    spans: List[Tuple[int, int]] = field(default_factory=list)
    severity: str = "medium"

class ScamScriptDetector:
    def __init__(self, thr=0.4):
        self.thr = thr
        
        self.patterns = {
            "arrest_threat": [
                r"\bdigital arrest\b",
                r"\barrest\b",
                r"\bpolice\b",
                r"\bcbi\b",
                r"\bcase\b",
                r"\bfir\b",
                r"\blegal action\b"
            ],
            "secrecy_demand": [
                r"\bsecret\b",
                r"\bconfidential\b",
                r"\bdon't tell\b",
            ],
            "urgent_transfer": [
                r"\btransfer\b",
                r"\bupi\b",
                r"\bgift card\b",
                r"\bwallet\b",
            ],
            "high_risk_keywords": [
                r"\botp\b",
                r"\bcvv\b",
                r"\bpin\b",
                r"\bpassword\b",
                r"\burgent\b",
                r"\bbank\b",
                r"\baccount\b"
            ]
        }
        self._re = {k: [re.compile(p, re.I) for p in v] for k, v in self.patterns.items()}

    def detect(self, text):
        if not text or not text.strip():
            return self._empty()

        t = text.strip()
        tactics = []

        for cat in self.patterns.keys():
            tac = self._scan(t, cat)
            if tac.matches:
                tactics.append(tac)

        score = self._risk(tactics)

        return {
            "is_scam": score >= self.thr, 
            "risk_score": score,
            "tactics": tactics,
            "tactic_names": [x.name for x in tactics],
            "categories": [x.category for x in tactics],
            "highlights": self._hl(tactics, t),
            "summary": self._summ(tactics, score, score >= self.thr),
            "word_count": len(t.split()), 
            "transcript_length": len(t),
        }

    def _scan(self, text, cat):
        m, sp = [], []
        for rx in self._re[cat]:
            for mt in rx.finditer(text):
                m.append(mt.group(0))
                sp.append((mt.start(), mt.end()))

        if not m:
            return ScamTactic(cat, cat, 0.0, [], [], "low")

        c = min(0.8 + (len(set(m)) - 1) * 0.05, 0.99)
        sev = "critical" if cat in ("arrest_threat", "urgent_transfer", "high_risk_keywords") else "high"
        return ScamTactic(cat, cat, c, m, sp, sev)

    def _risk(self, tac):
        if not tac: return 0.0
        
        # HACKATHON OVERRIDE: 
        # We removed the divisors and word-count penalties. 
        # A single "critical" match now guarantees a score of 0.80+ (Instant HIGH RISK)
        w = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.25}
        
        s = sum(x.confidence * w.get(x.severity, 0.5) for x in tac)
        s = min(s, 1.0) # Caps at 1.0 (100% Risk)
        
        return round(s, 4)

    def _hl(self, tac, text):
        hs = []
        for x in tac:
            for s, e in x.spans:
                hs.append({
                    "start": s, "end": e, "text": text[s:e],
                    "category": x.category, "tactic": x.name,
                    "confidence": x.confidence, "severity": x.severity
                })
        hs.sort(key=lambda h: h["start"])
        return hs

    def _summ(self, tac, score, is_scam):
        if not tac: 
            return "No scam tactics detected."
            
        nm = {
            "arrest_threat": "arrest threats", 
            "secrecy_demand": "secrecy demands", 
            "urgent_transfer": "urgent transfers", 
            "high_risk_keywords": "suspicious keywords"
        }
        
        d = ", ".join(nm.get(x.category, x.category) for x in tac)
        lv = "CRITICAL" if score >= 0.8 else "HIGH" if score >= 0.6 else "MEDIUM" if score >= 0.4 else "LOW"
        st = "SCAM DETECTED" if is_scam else "Suspicious context"
        
        return f"{st} — Risk: {score:.2f} ({lv}). Detected: {d}."

    def _empty(self):
        return {
            "is_scam": False, "risk_score": 0.0, "tactics": [],
            "tactic_names": [], "categories": [], "highlights": [],
            "summary": "No transcript provided.", "word_count": 0,
            "transcript_length": 0
        }

def detect_scam_script(text, thr=0.4):
    return ScamScriptDetector(thr=thr).detect(text)
