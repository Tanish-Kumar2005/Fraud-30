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
    def __init__(self, thr=0.5):
        self.thr = thr
        self.patterns = {
            "arrest_threat": [
                r"\bdigital arrest\b",
                r"\barrest\b.*\b(imminent|immediate|today|now)\b",
                r"\bpolice\b.*\b(arrest|custody|case|complaint|FIR)\b",
                r"\bCBI\b.*\b(arrest|case|investigation|raid)\b",
                r"\byou will be arrested\b",
                r"\blegal action\b.*\b(against you|taken)\b",
            ],
            "secrecy_demand": [
                r"\bdon't tell\b.*\b(anyone|anybody|family|friend)\b",
                r"\bdo not disclose\b",
                r"\bkeep this\b.*\b(confidential|secret|between us)\b",
                r"\bdon't inform\b.*\b(bank|police|family)\b",
            ],
            "urgent_transfer": [
                r"\btransfer\b.*\b(money|funds)\b.*\b(immediately|now|urgent)\b",
                r"\bwire\b.*\b(money|funds)\b.*\b(now|today|immediately)\b",
                r"\bsend\b.*\b(money|funds)\b.*\b(to this account|to this wallet)\b",
                r"\bUPI\b.*\b(ID|transfer|payment)\b.*\b(now|immediately|urgent)\b",
                r"\bgift card\b",
            ],
        }
        self._re = {k: [re.compile(p, re.I) for p in v] for k, v in self.patterns.items()}

    def detect(self, text):
        if not text or not text.strip():
            return self._empty()
        t = text.strip()
        tactics = []
        for cat in ["arrest_threat", "secrecy_demand", "urgent_transfer"]:
            tac = self._scan(t, cat)
            if tac.matches:
                tactics.append(tac)
        score = self._risk(tactics, len(t.split()))
        return {
            "is_scam": score >= self.thr, "risk_score": score,
            "tactics": tactics,
            "tactic_names": [x.name for x in tactics],
            "categories": [x.category for x in tactics],
            "highlights": self._hl(tactics, t),
            "summary": self._summ(tactics, score, score >= self.thr),
            "word_count": len(t.split()), "transcript_length": len(t),
        }

    def _scan(self, text, cat):
        m, sp = [], []
        for rx in self._re[cat]:
            for mt in rx.finditer(text):
                m.append(mt.group(0)); sp.append((mt.start(), mt.end()))
        if not m:
            return ScamTactic(cat, cat, 0.0, [], [], "low")
        c = min(0.8 + (len(set(m)) - 1) * 0.05, 0.99)
        sev = "critical" if cat in ("arrest_threat", "urgent_transfer") and c >= 0.85 else "high" if cat in ("arrest_threat", "urgent_transfer") else "medium"
        return ScamTactic(cat, cat, c, m, sp, sev)

    def _risk(self, tac, wc):
        if not tac: return 0.0
        w = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        s = sum(x.confidence * w.get(x.severity, 0.5) for x in tac) / 2.5
        s = min(s, 1.0)
        if len({x.category for x in tac}) >= 2: s = min(s + 0.1, 1.0)
        if len({x.category for x in tac}) >= 3: s = min(s + 0.1, 1.0)
        if wc < 10: s *= 0.8
        elif wc < 30: s *= 0.9
        return round(s, 4)

    def _hl(self, tac, text):
        hs = []
        for x in tac:
            for s, e in x.spans:
                hs.append({"start": s, "end": e, "text": text[s:e],
                           "category": x.category, "tactic": x.name,
                           "confidence": x.confidence, "severity": x.severity})
        hs.sort(key=lambda h: h["start"])
        return hs

    def _summ(self, tac, score, is_scam):
        if not tac: return "No scam tactics detected."
        nm = {"arrest_threat": "arrest threats", "secrecy_demand": "secrecy demands",
              "urgent_transfer": "urgent transfers"}
        d = ", ".join(nm.get(x.category, x.category) for x in tac)
        lv = "CRITICAL" if score >= 0.8 else "HIGH" if score >= 0.6 else "MEDIUM" if score >= 0.4 else "LOW"
        st = "SCAM DETECTED" if is_scam else "No clear scam indicators"
        return f"{st} — Risk: {score:.2f} ({lv}). Detected: {d}."

    def _empty(self):
        return {"is_scam": False, "risk_score": 0.0, "tactics": [],
                "tactic_names": [], "categories": [], "highlights": [],
                "summary": "No transcript provided.", "word_count": 0,
                "transcript_length": 0}

    def detect_from_file(self, path, enc="utf-8"):
        try:
            with open(path, "r", encoding=enc) as f:
                return self.detect(f.read())
        except FileNotFoundError:
            return {"error": f"Not found: {path}", "is_scam": False,
                    "risk_score": 0.0, "tactics": [], "tactic_names": [],
                    "categories": [], "highlights": [],
                    "summary": "Error: file not found.", "word_count": 0}


def detect_scam_script(text, thr=0.5):
    return ScamScriptDetector(thr=thr).detect(text)