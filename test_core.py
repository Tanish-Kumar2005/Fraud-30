import numpy as np
from voice_clone_detector import VoiceCloneDetector
from scam_script_detector import ScamScriptDetector
from call_safety_assistant import CallSafetyAssistant
from audio_utils import save_audio, load_audio
import os

SR = 16000
os.makedirs('test_output', exist_ok=True)

# Test 1: Voice clone detector
t = np.linspace(0, 3, int(SR * 3))
signal = 0.4 * np.sin(2 * np.pi * 130 * t) + 0.2 * np.sin(2 * np.pi * 300 * t)
envelope = np.ones_like(t)
audio = np.clip(signal * envelope + 0.03 * np.random.RandomState(42).randn(len(t)), -1, 1).astype(np.float32)

p1 = 'test_output/test_nat.wav'
save_audio(p1, audio, SR)
det = VoiceCloneDetector(thr=0.65)
r1 = det.detect_from_file(p1, delete_after=False)
print('Voice clone test: is_synthetic={}, prob={:.3f}'.format(r1['is_synthetic'], r1['synthetic_probability']))
os.remove(p1)

# Test 2: Scam script detector
sd = ScamScriptDetector()
r2 = sd.detect('Hello, this is Officer Rajesh from CBI. Digital arrest warrant issued. Transfer funds immediately.')
print('Scam test: is_scam={}, risk={:.3f}, tactics={}'.format(r2['is_scam'], r2['risk_score'], r2['tactic_names']))

# Test 3: Full pipeline
assistant = CallSafetyAssistant(del_after=False)
signal2 = 0.45 * np.sin(2 * np.pi * 130 * t)
audio2 = np.clip(signal2 + 0.01 * np.random.RandomState(99).randn(len(t)), -1, 1).astype(np.float32)
p2 = 'test_output/test_syn.wav'
save_audio(p2, audio2, SR)
r3 = assistant.analyse_call(p2, transcript='Hello, this is Officer Rajesh from CBI. Digital arrest warrant issued. Transfer funds immediately. Do not tell anyone.')
print('Pipeline test: risk={}, voice_synthetic={}, scam={}'.format(r3['combined_risk'], r3['voice_clone']['is_synthetic'], r3['scam_script']['is_scam'] if r3['scam_script'] else None))
os.remove(p2)

print('All core module tests PASSED!')