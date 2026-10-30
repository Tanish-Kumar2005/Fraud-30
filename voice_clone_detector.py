from typing import Dict, List, Tuple, Optional
import numpy as np
from audio_utils import extract_all_features, compute_feature_statistics, split_into_segments, load_audio, delete_audio_file


class VoiceCloneDetector:
    def __init__(self, sr=16000, thr=0.65, seg_dur=5.0, ov=0.5):
        self.sr=sr; self.thr=thr; self.seg_dur=seg_dur; self.ov=ov

    def detect_from_file(self, path, delete_after=False):
        a, sr = load_audio(path, target_sr=self.sr)
        r = self.detect_from_audio(a, sr)
        if delete_after: delete_audio_file(path)
        r["source_file"] = path
        return r

    def detect_from_audio(self, a, sr=None):
        sr = sr or self.sr
        if len(a) == 0: return self._empty()
        an = self._n(a)
        segs = split_into_segments(an, sr, segment_duration=self.seg_dur, overlap=self.ov)
        if not segs: return self._empty()
        rs, sc = [], []
        for sa, st, et in segs:
            stt = compute_feature_statistics(extract_all_features(sa, sr))
            sc_, reas = self._score(stt)
            rs.append({"start_time": st, "end_time": et, "synthetic_score": sc_,
                       "is_synthetic": sc_ >= self.thr, "features": stt, "reasons": reas})
            sc.append(sc_)
        avg = float(np.mean(sc))
        return {"is_synthetic": avg >= self.thr, "synthetic_probability": avg,
                "max_segment_score": float(np.max(sc)), "confidence": self._c(avg),
                "features": compute_feature_statistics(extract_all_features(an, sr)),
                "segment_results": rs, "reasons": self._agg(rs),
                "num_segments": len(rs), "sample_rate": sr, "duration": float(len(an)/sr)}

    def _score(self, st):
        s, r = 0.0, []
        if st.get("mfcc_std", 0) < 8.0: s += 0.2; r.append("Low MFCC variance")
        cs, cm = st.get("spectral_centroid_std", 0), st.get("spectral_centroid_mean", 1000.0)
        if cm > 0 and cs/cm < 0.10: s += 0.2; r.append("Centroid too stable")
        if st.get("zcr_mean", 0) < 0.05: s += 0.15; r.append("Low zero-crossing rate")
        if st.get("spectral_rolloff_mean", 0) < 2000.0: s += 0.15; r.append("Low spectral rolloff")
        if st.get("chroma_std", 0) < 0.02: s += 0.1; r.append("Flat chroma")
        rm, rmm = st.get("rms_std", 0), st.get("rms_mean", 0.01)
        if rmm > 0 and rm/rmm < 0.30: s += 0.1; r.append("Low RMS dynamics")
        if st.get("tempo", 100) < 40 or st.get("tempo", 100) > 220: s += 0.05; r.append(f"Unusual tempo: {st.get('tempo',100):.1f}")
        return min(s, 1.0), r

    def _agg(self, rs):
        seen, out = set(), []
        for seg in rs:
            for reason in seg.get("reasons", []):
                if reason not in seen: seen.add(reason); out.append(reason)
        return out

    def _c(self, score):
        if score >= 0.80: return "high"
        if score >= 0.65: return "medium"
        if score >= 0.40: return "low"
        return "very_low"

    def _empty(self):
        return {"is_synthetic": False, "synthetic_probability": 0.0, "max_segment_score": 0.0,
                "confidence": "very_low", "features": {}, "segment_results": [],
                "reasons": ["Insufficient audio"], "num_segments": 0, "sample_rate": self.sr, "duration": 0.0}

    @staticmethod
    def _n(a):
        p = np.max(np.abs(a))
        if p < 1e-9: return a
        return (a/p).astype(np.float32)


def detect_voice_clone(path, thr=0.65, delete_after=False):
    d = VoiceCloneDetector(thr=thr)
    return d.detect_from_file(path, delete_after=delete_after)