
import os
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional, Dict, List


def load_audio(file_path: str, target_sr: int = 16000, mono: bool = True, duration: Optional[float] = None, offset: float = 0.0,) -> Tuple[np.ndarray, int]:

    """Load an audio file and resample to the target sample rate."""
    if not os.path.exists(file_path):
    
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    audio, sr = librosa.load(
    
        file_path, sr=target_sr, mono=mono, duration=duration,
        offset=offset, res_type="kaiser_best",
    
    )
    
    return audio.astype(np.float32), sr


def save_audio(file_path: str, audio: np.ndarray, sr: int = 16000, subtype: str = "PCM_16",) -> None:

    """Save audio data to a file."""
    sf.write(file_path, audio, sr, subtype=subtype)


def delete_audio_file(file_path: str) -> bool:
    
    """Securely delete an audio file from disk after analysis."""
    try:
    
        if os.path.exists(file_path):
    
            os.remove(file_path)
            return True
    
        return False
    
    except OSError:
    
        return False


def compute_mfcc(audio: np.ndarray, sr: int, n_mfcc: int = 13, n_fft: int = 2048, hop_length: int = 512,) -> np.ndarray:
    
    """Compute Mel-frequency cepstral coefficients (MFCCs) for audio."""
    return librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft, hop_length=hop_length,)


def compute_spectral_centroid(audio: np.ndarray, sr: int, n_fft: int = 2048, hop_length: int = 512,) -> np.ndarray:
    
    """Compute the spectral centroid of the audio."""
    return librosa.feature.spectral_centroid(y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length,)


def compute_zero_crossing_rate(audio: np.ndarray, frame_length: int = 2048, hop_length: int = 512,) -> np.ndarray:

    """Compute the zero-crossing rate of the audio."""
    return librosa.feature.zero_crossing_rate(y=audio, frame_length=frame_length, hop_length=hop_length,)


def compute_spectral_rolloff(audio: np.ndarray, sr: int, n_fft: int = 2048,hop_length: int = 512, roll_percent: float = 0.85,) -> np.ndarray:
    
    """Compute the spectral rolloff point."""
    return librosa.feature.spectral_rolloff(y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length,roll_percent=roll_percent,)


def compute_chroma(audio: np.ndarray, sr: int, n_fft: int = 2048, hop_length: int = 512,) -> np.ndarray:

    """Compute chroma features from the audio."""
    return librosa.feature.chroma_stft(y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length,)


def extract_all_features(audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:

    """Extract a comprehensive set of audio features for voice analysis."""
    hop_length = 512
    n_fft = 2048
    mfcc = compute_mfcc(audio, sr, n_fft=n_fft, hop_length=hop_length)
    centroid = compute_spectral_centroid(audio, sr, n_fft=n_fft, hop_length=hop_length)
    zcr = compute_zero_crossing_rate(audio, frame_length=n_fft, hop_length=hop_length)
    rolloff = compute_spectral_rolloff(audio, sr, n_fft=n_fft, hop_length=hop_length)
    chroma = compute_chroma(audio, sr, n_fft=n_fft, hop_length=hop_length)
    rms = librosa.feature.rms(y=audio, frame_length=n_fft, hop_length=hop_length)
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    duration = librosa.get_duration(y=audio, sr=sr)
    
    return {
    
        "mfcc": mfcc,
        "spectral_centroid": centroid,
        "zcr": zcr,
        "spectral_rolloff": rolloff,
        "chroma": chroma,
        "rms": rms,
        "tempo": float(tempo) if np.isscalar(tempo) else float(tempo[0]),
        "duration": duration,
    
    }


def compute_feature_statistics(features: Dict[str, np.ndarray]) -> Dict[str, float]:
    
    """Compute summary statistics (mean, std, min, max) for each feature matrix."""
    stats: Dict[str, float] = {}
    
    for key, value in features.items():
    
        if isinstance(value, np.ndarray) and value.size > 0:
    
            stats[f"{key}_mean"] = float(np.mean(value))
            stats[f"{key}_std"] = float(np.std(value))
            stats[f"{key}_min"] = float(np.min(value))
            stats[f"{key}_max"] = float(np.max(value))
    
        elif isinstance(value, (int, float)):
    
            stats[key] = float(value)
    
    return stats


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    
    """Normalize audio to a target loudness level in dBFS."""
    rms = np.sqrt(np.mean(audio**2))
    
    if rms < 1e-9:
    
        return audio
    
    current_db = 20 * np.log10(rms + 1e-9)
    gain_db = target_db - current_db
    gain = 10 ** (gain_db / 20)
    normalized = audio * gain
    normalized = np.clip(normalized, -1.0, 1.0)
    return normalized.astype(np.float32)


def split_into_segments(audio: np.ndarray, sr: int, segment_duration: float = 5.0, overlap: float = 0.5,) -> List[Tuple[np.ndarray, float, float]]:
    
    """Split audio into overlapping segments for batch analysis."""
    segment_samples = int(segment_duration * sr)
    hop_samples = int(segment_samples * (1 - overlap))
    total_samples = len(audio)
    segments = []
    start = 0
    
    while start < total_samples:
    
        end = min(start + segment_samples, total_samples)
        segment = audio[start:end]
    
        if len(segment) < sr * 0.5:
            break
    
        segments.append((segment, start / sr, end / sr))
    
        if end >= total_samples:
            break
    
        start += hop_samples
    
    return segments