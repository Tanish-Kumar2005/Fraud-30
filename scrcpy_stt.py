"""
run_realtime_stt.py

Real-Time Call Transcription (speech_recognition backend):
- Intercepts master playback loopback tap via soundcard WASAPI.
- Anti-aliased 3-tap boxcar downsampler (48kHz -> 16kHz).
- Dynamic pause-aware utterance segmentation (3.2s to 6.5s window).
- Decodes via Google Web Speech API with sub-second turnaround.
- AUTOMATICALLY runs ScamScriptDetector AI on every transcribed chunk.
"""

from __future__ import annotations
from pathlib import Path
import queue
import sys
import threading
import time
import warnings
import numpy as np
import soundcard as sc
import sqlite3
import datetime

# ✅ 1. Import your AI Engine
from scam_script_detector import detect_scam_script

warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.stt_service import SpeechToTextService

# --- DATABASE SETUP (Replaces old database.py import) ---
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_label TEXT,
            source TEXT,
            transcript_text TEXT,
            ai_summary TEXT,
            risk_level TEXT
        )
    ''')
    # ✅ 2. Wipes the database clean every time a new session starts
    cursor.execute("DELETE FROM transcriptions")
    conn.commit()
    conn.close()

def save_to_db(text, risk_level, ai_summary):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    date_label = datetime.datetime.now().strftime("%H:%M:%S")
    cursor.execute(
        "INSERT INTO transcriptions (date_label, source, transcript_text, ai_summary, risk_level) VALUES (?, ?, ?, ?, ?)",
        (date_label, "System Audio", text, ai_summary, risk_level)
    )
    conn.commit()
    conn.close()


# --- AUDIO PIPELINE SETTINGS ---
SOURCE_SR = 48000
TARGET_SR = 16000
BLOCK_FRAMES = 4800                            # 100ms hardware slices @ 48kHz

# Pause-Aware Utterance Segmentation
MIN_CHUNK_SEC = 3.2                            # Minimum length before evaluating pauses
MAX_CHUNK_SEC = 6.5                            # Hard ceiling to force chunk dispatch
PAUSE_TRIGGER_SEC = 0.35                       # 350ms silence triggers boundary flush

MIN_SAMPLES = int(TARGET_SR * MIN_CHUNK_SEC)
MAX_SAMPLES = int(TARGET_SR * MAX_CHUNK_SEC)
PAUSE_SLICES_THRESHOLD = int(PAUSE_TRIGGER_SEC / (BLOCK_FRAMES / SOURCE_SR))

audio_queue: queue.Queue[tuple[int, np.ndarray]] = queue.Queue(maxsize=30)
stop_event = threading.Event()
print_lock = threading.Lock()


def select_default_loopback():
    """Binds strictly to the default physical speaker loopback."""
    loopbacks = [m for m in sc.all_microphones(include_loopback=True) if m.isloopback]
    if not loopbacks:
        print(" No WASAPI loopback device found. Check your sound drivers.")
        sys.exit(1)

    speaker = sc.default_speaker()
    clean_speaker_name = speaker.name.split("(")[0].strip().lower()

    selected_loopback = None
    for m in loopbacks:
        name_lower = m.name.lower()
        if "mic" in name_lower or "array" in name_lower or "cable" in name_lower:
            continue
        if clean_speaker_name in name_lower or speaker.name.lower() in name_lower:
            selected_loopback = m
            break

    if selected_loopback is None:
        selected_loopback = next(
            (m for m in loopbacks if "cable" not in m.name.lower() and "mic" not in m.name.lower()),
            loopbacks[0],
        )

    return speaker, selected_loopback


def anti_aliased_downsample(stereo_48k: np.ndarray) -> np.ndarray:
    """Averages 3-sample blocks from 48kHz to 16kHz mono to prevent foldover aliasing."""
    if stereo_48k.ndim > 1:
        mono_48k = stereo_48k.mean(axis=1).astype(np.float32)
    else:
        mono_48k = stereo_48k.astype(np.float32)

    usable_len = (len(mono_48k) // 3) * 3
    if usable_len == 0:
        return np.zeros(0, dtype=np.float32)

    return mono_48k[:usable_len].reshape(-1, 3).mean(axis=1)


def transcription_worker(stt: SpeechToTextService):
    """Consumer thread: decodes Chunk N via API while Chunk N+1 records in parallel."""
    while not stop_event.is_set():
        try:
            chunk_id, audio_array = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        raw_peak = float(np.max(np.abs(audio_array)))
        audio_seconds = round(len(audio_array) / TARGET_SR, 1)

        result = stt.transcribe_array(audio_array)

        with print_lock:
            sys.stdout.write("\r" + " " * 95 + "\r")
            if result.get("success"):
                transcript = result.get("transcript", "").strip()
                if transcript:
                    
                    # ✅ 3. AI THREAT ANALYSIS
                    ai_result = detect_scam_script(transcript)
                    risk_score = ai_result["risk_score"]
                    ai_summary = ai_result["summary"]
                    
                    if risk_score >= 0.6:
                        risk_level = "HIGH"
                    elif risk_score >= 0.4:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"
                        # Fallback for clean terminal view if it's completely safe
                        if "No transcript provided" in ai_summary or risk_score == 0.0:
                            ai_summary = "Routine conversation. No direct threats detected."

                    # ✅ 4. SAVE TO SQLITE DATABASE
                    save_to_db(transcript, risk_level, ai_summary)

                    ts = time.strftime("%H:%M:%S")
                    print(
                        f"[{ts}] 🚨 {risk_level} RISK | Chunk #{chunk_id:03d} "
                        f"({audio_seconds}s audio | {result['inference_time']}s API | {result['language']}):\n"
                        f" \"{transcript}\"\n"
                        f" ➔ AI Output: {ai_summary}\n"
                    )
                else:
                    print(f" [Chunk #{chunk_id:03d}] Inaudible / Skipped by API (Peak: {raw_peak:.4f})")
            elif result.get("error"):
                print(f" Error on Chunk #{chunk_id:03d}: {result['error']}")

        audio_queue.task_done()


def main():
    # ✅ Initialize and WIPE database before we start listening
    init_db()

    print("=" * 76)
    print("   REAL-TIME CALL TRANSCRIPTION (speech_recognition backend)   ")
    print("=" * 76)

    speaker, loopback_mic = select_default_loopback()
    print(f" Output Playback : {speaker.name}")
    print(f" Loopback Tap    : {loopback_mic.name}\n")

    # Change primary_language to "en-IN" if calls are mostly in English
    stt = SpeechToTextService(primary_language="en-IN", fallback_language="en-IN", sample_rate=TARGET_SR)
    print(f" STT Engine      : Google Web Speech (Primary: {stt.primary_language} | Fallback: {stt.fallback_language})")

    worker_thread = threading.Thread(target=transcription_worker, args=(stt,), daemon=True)
    worker_thread.start()

    print("\n Monitoring active audio stream...")
    print(" Database wiped. Stream active. Press Ctrl+C to stop.\n" + "-" * 76)

    chunk_id = 1
    buffer_16k = np.zeros(0, dtype=np.float32)
    silence_slices = 0

    try:
        with loopback_mic.recorder(samplerate=SOURCE_SR, channels=2, blocksize=BLOCK_FRAMES) as mic:
            while True:
                stereo_48k = mic.record(numframes=BLOCK_FRAMES)
                mono_16k = anti_aliased_downsample(stereo_48k)
                buffer_16k = np.concatenate((buffer_16k, mono_16k))

                current_sec = len(buffer_16k) / TARGET_SR
                slice_peak = float(np.max(np.abs(mono_16k))) if len(mono_16k) > 0 else 0.0

                # Pause threshold: slice_peak < 0.005 indicates pause/silence
                if slice_peak < 0.005:
                    silence_slices += 1
                else:
                    silence_slices = 0

                activity_icon = " [SPEECH]" if slice_peak > 0.012 else ("🔉 [FAINT]" if slice_peak > 0.003 else "🔇 [PAUSE]")

                with print_lock:
                    sys.stdout.write(
                        f"\r  Recording Chunk #{chunk_id:03d}: [{current_sec:4.1f}s / max {MAX_CHUNK_SEC:.1f}s] "
                        f"| Peak: {slice_peak:.4f} {activity_icon}"
                    )
                    sys.stdout.flush()

                should_dispatch = False
                if len(buffer_16k) >= MIN_SAMPLES and silence_slices >= PAUSE_SLICES_THRESHOLD:
                    should_dispatch = True
                elif len(buffer_16k) >= MAX_SAMPLES:
                    should_dispatch = True

                if should_dispatch:
                    # Ignore pure digital flatlines (< 0.002 peak)
                    if float(np.max(np.abs(buffer_16k))) >= 0.002:
                        payload = buffer_16k.copy()
                        audio_queue.put((chunk_id, payload))

                        with print_lock:
                            sys.stdout.write("\r" + " " * 95 + "\r")
                            print(
                                f" Dispatched Chunk #{chunk_id:03d} ({len(payload)/TARGET_SR:.1f}s phrase). "
                                f"Recording Chunk #{chunk_id + 1:03d}..."
                            )

                        chunk_id += 1

                    buffer_16k = np.zeros(0, dtype=np.float32)
                    silence_slices = 0

    except KeyboardInterrupt:
        print("\n\n  Stopping monitor...")
        stop_event.set()
        worker_thread.join(timeout=1.0)
        print(" Finished.")

if __name__ == "__main__":
    main()
