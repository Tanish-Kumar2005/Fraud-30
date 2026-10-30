import os
import numpy as np
from call_safety_assistant import CallSafetyAssistant
from audio_utils import save_audio
from voice_clone_detector import VoiceCloneDetector
from scam_script_detector import ScamScriptDetector

SR = 16000
OUT = 'demo_output'

def generate_natural_voice(duration=5.0):

    t = np.linspace(0, duration, int(SR * duration))
    f0 = 120 + 8 * np.sin(2 * np.pi * 5 * t)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    signal = np.zeros_like(t)
    
    for f in [300, 900, 2400]:
    
        signal += 0.3 * np.sin(2 * np.pi * f * t)
    
    signal += 0.4 * np.sin(phase)
    envelope = np.ones_like(t)
    attack = int(0.1 * SR); release = int(0.2 * SR)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    noise = 0.05 * np.random.RandomState(42).randn(len(t))
    return np.clip(signal * envelope + noise, -1, 1).astype(np.float32)

def generate_synthetic_voice(duration=5.0):
    
    t = np.linspace(0, duration, int(SR * duration))
    phase = 2 * np.pi * 130 * t
    signal = np.zeros_like(t)
    
    for f in [350, 850, 2200]:
    
        signal += 0.25 * np.sin(2 * np.pi * f * t)
    
    signal += 0.45 * np.sin(phase)
    envelope = np.full_like(t, 0.85)
    noise = 0.01 * np.random.RandomState(99).randn(len(t))
    
    return np.clip(signal * envelope + noise, -1, 1).astype(np.float32)

def generate_scam_transcript():
    
    return ('Hello, this is Officer Rajesh from CBI. Digital arrest warrant '
            'issued. Transfer funds immediately to avoid arrest. Do not tell '
            'anyone about this call. Send money via UPI right now.')

def generate_safe_transcript():
    
    return ('Hello, I am calling from your bank. Your monthly statement '
            'is available online. Visit our website or call back if needed.')

def run_voice_demo():
    
    print('=' * 60)
    print('DEMO 1: Voice-Clone Detection')
    print('=' * 60)
    os.makedirs(OUT, exist_ok=True)
    nat = generate_natural_voice(5.0)
    syn = generate_synthetic_voice(5.0)
    p1 = os.path.join(OUT, 'nat.wav')
    p2 = os.path.join(OUT, 'syn.wav')
    save_audio(p1, nat, SR)
    save_audio(p2, syn, SR)
    det = VoiceCloneDetector(thr=0.65)
    r1 = det.detect_from_file(p1, delete_after=False)
    r2 = det.detect_from_file(p2, delete_after=False)
    print('Natural voice: synthetic={}'.format(r1['is_synthetic']))
    print('  Probability: {:.3f}, Confidence: {}'.format(r1['synthetic_probability'], r1['confidence']))
    print('Synthetic voice: synthetic={}'.format(r2['is_synthetic']))
    print('  Probability: {:.3f}, Confidence: {}'.format(r2['synthetic_probability'], r2['confidence']))
    os.remove(p1); os.remove(p2)

def run_scam_demo():
    
    print()
    print('=' * 60)
    print('DEMO 2: Scam Script Detection')
    print('=' * 60)
    d = ScamScriptDetector()
    r1 = d.detect(generate_scam_transcript())
    print('Scam transcript: is_scam={}, risk={:.3f}, tactics={}'.format(
        r1['is_scam'], r1['risk_score'], r1['tactic_names']))
    r2 = d.detect(generate_safe_transcript())
    print('Safe transcript: is_scam={}, risk={:.3f}, summary={}'.format(
        r2['is_scam'], r2['risk_score'], r2['summary']))

def run_pipeline_demo():
    
    print()
    print('=' * 60)
    print('DEMO 3: Full Call-Safety Pipeline')
    print('=' * 60)
    os.makedirs(OUT, exist_ok=True)
    assistant = CallSafetyAssistant(del_after=False)
    print('--- Scenario A: Synthetic voice + scam tactics (CRITICAL) ---')
    sa = generate_synthetic_voice(5.0)
    p1 = os.path.join(OUT, 'scam.wav')
    save_audio(p1, sa, SR)
    r = assistant.analyse_call(p1, transcript=generate_scam_transcript())
    print('Risk: {}'.format(r['combined_risk'].upper()))
    print('Voice: synthetic={}'.format(r['voice_clone']['is_synthetic']))
    print('Scam: detected={}'.format(r['scam_script']['is_scam']))
    print('Recommendation: {}'.format(r['recommendation']))
    os.remove(p1)
    print('--- Scenario B: Natural voice + safe transcript (SAFE) ---')
    na = generate_natural_voice(5.0)
    p2 = os.path.join(OUT, 'safe.wav')
    save_audio(p2, na, SR)
    r2 = assistant.analyse_call(p2, transcript=generate_safe_transcript())
    print('Risk: {}'.format(r2['combined_risk'].upper()))
    print('Voice: synthetic={}'.format(r2['voice_clone']['is_synthetic']))
    print('Scam: detected={}'.format(r2['scam_script']['is_scam']))
    print('Recommendation: {}'.format(r2['recommendation']))
    os.remove(p2)

def main():
    
    run_voice_demo()
    run_scam_demo()
    run_pipeline_demo()
    print()
    print('=' * 60)
    print('Demo complete.')
    print('=' * 60)

if __name__ == '__main__':

    main()
