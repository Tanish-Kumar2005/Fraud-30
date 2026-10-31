import speech_recognition as sr
from typing import Dict,Any, Optional

#recognizer
_recognizer = sr.Recognizer()

def transcribe_audio_data(
        audio_data: sr.AudioData,
        language: str = 'en-IN',
) -> Dict[str,Any]:
    try:
        text = _recognizer.recognize_google(audio_data, language=language)
        return {'Success': True, "text":text,"error": None}

    except sr.UnknownValueError:
        return{ 
            "Success": False,
            "Text": None,
            "error": "Speech was detected but was not understood",
        }
    except sr.RequestError as e:
            return{ 
                "Success": False,
                "Text": None,
                "error": f"Recognition Service request failed: {e}",
            }
    except Exception as e:
                return{ 
                    "Success": False,
                    "Text": None,
                    "error": f"Unexpected Error: {e}",
                }
def transcribe_raw_bytes(
            audio_bytes: bytes,
            sample_rate: int = 16000,
            sample_width: int = 2,
            language: str = "en-IN",
)->Dict[str, Any]:
      try:
            audio_data = sr.AudioData(audio_bytes, sample_rate, sample_width)
            return transcribe_audio_data(audio_data, language=language)
      except Exception as e:
            return{
                  "Success":False,
                  "text": None,
                  "error": f"Failed to construct AudioData from raw bytes: {e}",
                  
            }
def transcribe_file(
            audio_file_path: str,
            language: str = "en-IN",
            offset: Optional[float] = None,
            duration: Optional[float] = None,
)->Dict[str, Any]:
      try:
            with sr.AudioFile(audio_file_path) as source:
                  audio_data = _recognizer.record(source, offset=offset, duration=duration) 
            return transcribe_audio_data(audio_data,language=language)
      except FileNotFoundError:
            return{
                  "success":False,
                  "text":None,
                  "error": f"audio file not found at {audio_file_path}",
            }
      except Exception as e:
                  return{
                        "success":False,
                        "text":None,
                        "error": f"Error reading audio file: {e}",
                  }
            