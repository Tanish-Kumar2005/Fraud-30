from __future__ import annotations

import logging
import time
from typing import Any
import numpy as np
import speech_recognition as sr

logger = logging.getLogger(__name__)


class SpeechToTextService:

    def __init__(
        self,
        # Default: 'hi-IN' for Hindi. Set primary to 'en-IN' if calls are mostly English.
        primary_language: str = "hi-IN",
        fallback_language: str = "en-IN",
        sample_rate: int = 16000,
    ):
        
        self.language = primary_language
        self.primary_language = primary_language
        self.fallback_language = fallback_language
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()

        # 250ms digital silence cushion (4000 samples @ 16kHz)
        self._pad_samples = int(self.sample_rate * 0.25)
        self._silence_pad = np.zeros(self._pad_samples, dtype=np.float32)

    def _prepare_audio(self, audio_array: np.ndarray) -> sr.AudioData:
        
        """Scales active speech to a safe 0.65 peak and wraps into 16-bit PCM AudioData."""
        peak = float(np.max(np.abs(audio_array)))
        
        if peak >= 0.01:
        
            scaled = audio_array * (0.65 / peak)
        
        elif peak >= 0.002:
        
            scaled = audio_array * min(3.0, 0.65 / peak)
        
        else:
        
            scaled = audio_array

        # Sandwich between silence pads so Google's VAD resolves boundary consonants
        cushioned = np.concatenate((self._silence_pad, scaled, self._silence_pad))
        pcm_bytes = (cushioned * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
        return sr.AudioData(pcm_bytes, sample_rate=self.sample_rate, sample_width=2)

    def transcribe_array(self, audio_array: np.ndarray) -> dict[str, Any]:
        
        if audio_array.size == 0:
        
            return {"success": False, "transcript": "", "error": "Empty buffer"}

        duration = round(len(audio_array) / self.sample_rate, 2)
        audio_data = self._prepare_audio(audio_array)
        t0 = time.perf_counter()

        # Pass 1: Try Primary Language
        try:
        
            transcript = self.recognizer.recognize_google(audio_data, language=self.primary_language)
        
            return {
        
                "success": True,
                "transcript": transcript,
                "language": self.primary_language.upper(),
                "duration": duration,
                "inference_time": round(time.perf_counter() - t0, 3),
                "error": None,
        
            }
        
        except sr.UnknownValueError:
        
            pass  # Fall through to Pass 2
        
        except sr.RequestError as exc:
        
            return {
        
                "success": False,
                "transcript": "",
                "language": self.primary_language.upper(),
                "duration": duration,
                "inference_time": round(time.perf_counter() - t0, 3),
                "error": f"API Error: {exc}",
        
            }

        # Pass 2: Fallback Language
        try:
        
            transcript = self.recognizer.recognize_google(audio_data, language=self.fallback_language)
        
            return {
        
                "success": True,
                "transcript": transcript,
                "language": self.fallback_language.upper(),
                "duration": duration,
                "inference_time": round(time.perf_counter() - t0, 3),
                "error": None,
        
            }
        
        except sr.UnknownValueError:
        
            return {
            
                "success": True,
                "transcript": "",
                "language": "NONE",
                "duration": duration,
                "inference_time": round(time.perf_counter() - t0, 3),
                "error": None,
            
            }
        
        except Exception as exc:
            
            return {
            
                "success": False,
                "transcript": "",
                "language": "UNKNOWN",
                "duration": duration,
                "inference_time": round(time.perf_counter() - t0, 3),
                "error": str(exc),
            
            }