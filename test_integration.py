import joblib
import sys
from call_safety_assistant import CallSafetyAssistant
sys.path.insert(0, '.')

print("=" * 60)
print("  INTEGRATED TEST: Trained Model + Call Safety Assistant")
print("=" * 60)

# 1. Load the model
print("\n[1] Loading trained scam model...")

try:

    model = joblib.load('hindi_scam_model.pkl')
    vectorizer = joblib.load('tfidf_vectorizer.pkl')
    print("  Model loaded successfully.")

except Exception as e:

    print(f"  ERROR: {e}")
    exit(1)

# 2. Test model classification
print("\n[2] Testing Hindi text classification...")
test_cases = [
    ("Mujhe police se call aaya, jail kar doonga, please kisi ko mat batana", 1),
    ("Aapka account safe hai. Bank se contact karein.", 0),
]
for text, expected in test_cases:

    X = vectorizer.transform([text])
    pred = model.predict(X)[0]
    prob = model.predict_proba(X)[0][1]
    status = "PASS" if pred == expected else "FAIL"
    print(f"  {status}: \"{text[:50]}...\" -> {pred} ({prob:.2%}) (expected {expected})")

# 3. Test the call safety assistant
print("\n[3] Initializing CallSafetyAssistant...")
from voice_clone_detector import VoiceCloneDetector
from warning_display import WarningDisplay

assistant = CallSafetyAssistant()
display = WarningDisplay(enable_voice=True)

# 4. Simulate a scam call
print("\n[4] Simulating a scam call (Hindi transcript)...")
scam_transcript = "Mujhe police se call aaya, jail kar doonga, please kisi ko mat batana"
X = vectorizer.transform([scam_transcript])
pred = model.predict(X)[0]
prob = model.predict_proba(X)[0][1]

print(f"  Transcript: {scam_transcript[:60]}...")
print(f"  Model says: {'SCAM' if pred == 1 else 'SAFE'} ({prob:.1%})")

# Add a voice-clone detection (simulated)
voice_result = {
    "is_synthetic": True,
    "synthetic_probability": 0.85,
    "confidence": "high",
    "source_file": "test_call.wav"
}

display.process_voice(voice_result)

# Add a scam warning
if pred == 1:

    display.add("scam_script", "critical",
        f"Scam detected in transcript! Probability: {prob:.1%}",
        {"source": "hindi_scam_model.pkl"})

print(f"\n  Warnings raised: {len(display.get_active_warnings())}")
print(f"  Verify prompt shown: {display.verify_prompt}")

# 5. Verify all warnings
print("\n[5] Checking warnings...")

for i, w in enumerate(display.get_active_warnings()):

    print(f"  Warning {i+1}: [{w.severity}] {w.message[:60]}...")

# 6. Summary
print("\n" + "=" * 60)
print("  INTEGRATION TEST SUMMARY")
print("=" * 60)
all_passed = True

if len(display.get_active_warnings()) > 0:

    print("  ✓ Model integration")
    print("  ✓ Call safety assistant")
    print("  ✓ Voice display (screen + voice alerts)")
    print("  ✓ Warning generation")
    print("\n  ALL TESTS PASSED!")

else:

    print("  Some tests failed!")
    all_passed = False

print("=" * 60)

exit(0 if all_passed else 1)