"""
test_detectors.py - Unit tests for the Fraud 30 Voice-Clone Call Detector

Run with:
    python test_detectors.py -v
"""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_utils import (load_audio, save_audio, delete_audio_file,
                         compute_mfcc, compute_spectral_centroid,
                         compute_zero_crossing_rate, compute_spectral_rolloff,
                         compute_chroma, extract_all_features,
                         compute_feature_statistics, normalize_audio,
                         split_into_segments)
from voice_clone_detector import VoiceCloneDetector, detect_voice_clone
from scam_script_detector import ScamScriptDetector, detect_scam_script, ScamTactic
from warning_display import WarningDisplay, CallWarning
from call_safety_assistant import CallSafetyAssistant, analyse_call

SR = 16000
TD = "test_output"


def gen_audio(duration=2.0, synthetic=False):

    """Generate a simple test audio signal."""
    t = np.linspace(0, duration, int(SR * duration))

    if synthetic:

        signal = 0.5 * np.sin(2 * np.pi * 130 * t) + 0.2 * np.sin(2 * np.pi * 260 * t)
        envelope = np.full_like(t, 0.8)

    else:

        f0 = 120 + 10 * np.sin(2 * np.pi * 5 * t)
        phase = 2 * np.pi * np.cumsum(f0) / SR
        signal = 0.4 * np.sin(phase) + 0.2 * np.sin(2 * np.pi * 300 * t)
        envelope = np.ones_like(t)

    return np.clip(signal * envelope + 0.03 * np.random.RandomState(42).randn(len(t)), -1, 1).astype(np.float32)


class TestAudioUtils(unittest.TestCase):

    """Tests for audio_utils.py"""

    def setUp(self):

        os.makedirs(TD, exist_ok=True)
        self.audio = gen_audio()
        self.test_file = os.path.join(TD, "test_audio.wav")

    def test_save_and_load(self):

        save_audio(self.test_file, self.audio, SR)
        self.assertTrue(os.path.exists(self.test_file))
        loaded, sr = load_audio(self.test_file, target_sr=SR)
        self.assertEqual(sr, SR)
        self.assertGreater(len(loaded), 0)
        delete_audio_file(self.test_file)

    def test_delete_file(self):

        save_audio(self.test_file, self.audio, SR)
        self.assertTrue(os.path.exists(self.test_file))
        result = delete_audio_file(self.test_file)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.test_file))

    def test_delete_nonexistent(self):

        result = delete_audio_file(os.path.join(TD, "nonexistent.wav"))
        self.assertFalse(result)

    def test_mfcc(self):

        mfcc = compute_mfcc(self.audio, SR)
        self.assertEqual(mfcc.shape[0], 13)
        self.assertGreater(mfcc.shape[1], 0)

class TestVoiceCloneDetector(unittest.TestCase):

    """Tests for voice_clone_detector.py"""

    def setUp(self):

        os.makedirs(TD, exist_ok=True)
        self.detector = VoiceCloneDetector()

    def test_detect_natural_voice(self):

        audio = gen_audio(duration=3.0, synthetic=False)
        result = self.detector.detect_from_audio(audio, SR)
        self.assertIn("is_synthetic", result)
        self.assertIn("synthetic_probability", result)
        self.assertIn("confidence", result)

    def test_detect_file(self):

        audio = gen_audio()
        test_file = os.path.join(TD, "test_detect.wav")
        save_audio(test_file, audio, SR)
        result = self.detector.detect_from_file(test_file, delete_after=False)
        self.assertIsInstance(result["is_synthetic"], bool)
        self.assertIn("synthetic_probability", result)
        delete_audio_file(test_file)

    def test_delete_after_analysis(self):

        audio = gen_audio()
        test_file = os.path.join(TD, "test_delete.wav")
        save_audio(test_file, audio, SR)
        self.assertTrue(os.path.exists(test_file))
        result = self.detector.detect_from_file(test_file, delete_after=True)
        self.assertFalse(os.path.exists(test_file))
        self.assertIsInstance(result["is_synthetic"], bool)

    def test_empty_audio(self):

        empty_audio = np.array([], dtype=np.float32)
        result = self.detector.detect_from_audio(empty_audio, SR)
        self.assertFalse(result["is_synthetic"])

    def test_confidence_levels(self):

        # Check that confidence is derived from the threshold
        self.assertEqual(self.detector.thr, 0.65)

    def test_convenience_function(self):

        audio = gen_audio()
        test_file = os.path.join(TD, "test_conv.wav")
        save_audio(test_file, audio, SR)
        result = detect_voice_clone(test_file, thr=0.65, delete_after=False)
        self.assertIn("is_synthetic", result)
        delete_audio_file(test_file)


class TestScamScriptDetector(unittest.TestCase):

    """Tests for scam_script_detector.py"""

class TestCallSafetyAssistant(unittest.TestCase):

    """Tests for call_safety_assistant.py"""

    def setUp(self):

        os.makedirs(TD, exist_ok=True)
        self.audio = gen_audio()
        self.test_file = os.path.join(TD, "test_assistant.wav")
        save_audio(self.test_file, self.audio, SR)

    def tearDown(self):

        if os.path.exists(self.test_file):

            os.remove(self.test_file)

    def test_analyse_call(self):
        
        assistant = CallSafetyAssistant()
        result = assistant.analyse_call(self.test_file)
        self.assertIn("combined_risk", result)
        self.assertIn(result["combined_risk"],
                      ["safe", "caution", "warning", "critical"])
        self.assertIn("recommendation", result)

    def test_analyse_call_with_scam(self):

        assistant = CallSafetyAssistant()
        transcript = "Digital arrest warrant. Transfer money now. Don't tell anyone."
        result = assistant.analyse_call(self.test_file, transcript=transcript)
        self.assertTrue(result["scam_script"]["is_scam"])
        self.assertIn(result["combined_risk"], ["warning", "critical"])

    def test_convenience_function(self):
        
        result = analyse_call(
            self.test_file,
            transcript="Hello, this is a normal call.",
            delete_audio=False
        )
        
        self.assertIn("combined_risk", result)


if __name__ == "__main__":
    
    import shutil
    
    if os.path.exists(TD):
    
        shutil.rmtree(TD)
    
    os.makedirs(TD, exist_ok=True)
    unittest.main()

    def setUp(self):
    
        self.detector = ScamScriptDetector()

    def test_scam_detected(self):
    
        transcript = "Digital arrest warrant. Transfer money now. Don't tell anyone."
        result = self.detector.detect(transcript)
        self.assertTrue(result["is_scam"])
        self.assertGreater(result["risk_score"], 0.5)

    def test_clean_transcript(self):
    
        transcript = "Hello, your bank statement is available online."
        result = self.detector.detect(transcript)
        self.assertFalse(result["is_scam"])

    def test_empty_transcript(self):
    
        result = self.detector.detect("")
        self.assertFalse(result["is_scam"])

    def test_highlights(self):
    
        transcript = "Digital arrest. Transfer now."
        result = self.detector.detect(transcript)
        self.assertGreater(len(result["highlights"]), 0)

    def test_convenience_function(self):
    
        result = detect_scam_script("Digital arrest. Transfer money.")
        self.assertIn("is_scam", result)

    def test_scam_tactic_dataclass(self):
    
        tactic = ScamTactic(
            name="Test", category="test", confidence=0.8,
            matches=["test"], spans=[(0, 10)], severity="high"
        )
    
        self.assertEqual(tactic.name, "Test")
        self.assertEqual(tactic.confidence, 0.8)


class TestWarningDisplay(unittest.TestCase):
    
    """Tests for warning_display.py"""

    def setUp(self):
    
        self.display = WarningDisplay()

    def test_add_warning(self):
    
        warning = self.display.add("voice_clone", "high", "Test warning")
        self.assertIsInstance(warning, CallWarning)
        self.assertEqual(warning.warning_type, "voice_clone")

    def test_ack_warning(self):
    
        self.display.add("voice_clone", "high", "Warning 1")
        self.assertTrue(self.display.acknowledge(0))
        self.assertFalse(self.display.acknowledge(99))

    def test_clear_warnings(self):
    
        self.display.add("voice_clone", "high", "Warning 1")
        self.display.clear()
        self.assertEqual(len(self.display.active_warnings), 0)

    def test_verify_prompt(self):
    
        self.display.add("voice_clone", "critical", "Critical warning")
        self.assertTrue(self.display.verify_prompt)

    def test_process_voice(self):
    
        result = {"is_synthetic": True, "synthetic_probability": 0.9,
                  "confidence": "high"}
    
        warning = self.display.process_voice(result)
        self.assertIsNotNone(warning)
        self.assertEqual(warning.severity, "critical")

    def test_process_no_voice(self):
    
        result = {"is_synthetic": False, "synthetic_probability": 0.1}
        warning = self.display.process_voice(result)
        self.assertIsNone(warning)

    def test_process_scam(self):
    
        result = {"is_scam": True, "risk_score": 0.8,
                  "summary": "Scam detected"}
    
        warnings = self.display.process_scam(result)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].severity, "critical")

    def test_process_both(self):
    
        voice_result = {"is_synthetic": True, "synthetic_probability": 0.9}
        scam_result = {"is_scam": True, "risk_score": 0.9}
        warnings = self.display.process_both(voice_result, scam_result)
        self.assertGreaterEqual(len(warnings), 2)

    def test_spectral_centroid(self):
    
        centroid = compute_spectral_centroid(self.audio, SR)
        self.assertEqual(centroid.shape[0], 1)

    def test_zero_crossing_rate(self):
    
        zcr = compute_zero_crossing_rate(self.audio)
        self.assertEqual(zcr.shape[0], 1)

    def test_spectral_rolloff(self):
    
        rolloff = compute_spectral_rolloff(self.audio, SR)
        self.assertEqual(rolloff.shape[0], 1)

    def test_chroma(self):
    
        chroma = compute_chroma(self.audio, SR)
        self.assertEqual(chroma.shape[0], 12)

    def test_extract_all_features(self):
    
        features = extract_all_features(self.audio, SR)
        self.assertIn("mfcc", features)
        self.assertIn("tempo", features)
        self.assertIn("duration", features)

    def test_feature_statistics(self):
    
        stats = compute_feature_statistics(extract_all_features(self.audio, SR))
        self.assertIn("mfcc_mean", stats)
        self.assertIn("mfcc_std", stats)

    def test_normalize_audio(self):
    
        normalized = normalize_audio(self.audio, target_db=-20.0)
        self.assertTrue(np.all(np.abs(normalized) <= 1.0))

    def test_split_segments(self):
    
        segments = split_into_segments(self.audio, SR, segment_duration=1.0, overlap=0.0)
        self.assertGreater(len(segments), 0)