# utils/audio_utils.py
"""
Updated audio utilities for EchoViva 2.0

- Initializes TTS per-call (avoids pyttsx3 stalling after first utterance).
- Records audio with SpeechRecognition, returns (text, avg_volume) when requested.
- Uses a short timeout/phrase_time_limit so stepwise flow stays responsive.
- Defensive: handles missing microphone, API errors, and returns empty strings on failure.
"""

import speech_recognition as sr
import pyttsx3
import audioop
import wave
import tempfile
import os
import time

def _init_tts_engine():
    """Create and return a new pyttsx3 engine instance configured for speaking."""
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 170)
        engine.setProperty("volume", 0.9)
        voices = engine.getProperty("voices")
        if len(voices) > 1:
            # prefer a female voice if available (index may vary by OS)
            try:
                engine.setProperty("voice", voices[1].id)
            except Exception:
                pass
        return engine
    except Exception as e:
        print("[TTS init error]", e)
        return None


def speak(text: str):
    """
    Speak the given text aloud.

    This initializes a fresh pyttsx3 engine for each call to avoid the engine
    getting stuck after the first utterance in some environments.
    """
    if not text:
        return
    engine = _init_tts_engine()
    if engine is None:
        print("[TTS unavailable] would say:", text)
        return
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("[TTS error]", e)
    finally:
        try:
            engine.stop()
        except Exception:
            pass


def record_answer(duration: int = 8, get_volume: bool = False):
    """
    Record audio from the default microphone.

    Args:
        duration: maximum seconds to listen (phrase_time_limit).
        get_volume: if True, return (recognized_text, avg_volume)
                    otherwise return recognized_text.

    Returns:
        recognized_text (str) or (recognized_text (str), avg_volume (float))
        avg_volume is normalized RMS (0.0 - 1.0). On failure avg_volume = 0.0
    """
    recognizer = sr.Recognizer()

    # Try to open microphone; handle errors gracefully
    try:
        mic = sr.Microphone()
    except Exception as e:
        print("[Microphone error]", e)
        return ("", 0.0) if get_volume else ""

    with mic as source:
        # Short ambient adjustment to reduce noise impact
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
        except Exception:
            # ignore failures in ambient adjustment
            pass

        print("🎙 Listening... (please speak)")
        try:
            # timeout = maximum waiting time for phrase to start
            # phrase_time_limit = max duration of the phrase itself
            audio = recognizer.listen(source, timeout=duration, phrase_time_limit=duration)
        except sr.WaitTimeoutError:
            print("⚠️ Timeout: no speech detected.")
            return ("", 0.0) if get_volume else ""

    # Prepare to compute avg volume (RMS)
    avg_volume = 0.0
    try:
        wav_bytes = audio.get_wav_data()
        # write to temp file for wave reading
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
            tf.write(wav_bytes)
            temp_path = tf.name

        with wave.open(temp_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            # sample width (bytes) used by audioop.rms; use 2 (16-bit) most common
            sample_width = wf.getsampwidth() or 2
            try:
                rms = audioop.rms(frames, sample_width)
                # Normalize RMS by max 16-bit value (32768) to 0..1
                avg_volume = min(max(rms / 32768.0, 0.0), 1.0)
            except Exception:
                avg_volume = 0.0

        # remove temp file
        try:
            os.remove(temp_path)
        except Exception:
            pass
    except Exception as e:
        print("[Volume calc error]", e)
        avg_volume = 0.0

    # Recognize speech (Google free service)
    text = ""
    try:
        text = recognizer.recognize_google(audio)
        print("🧠 Recognized:", text)
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
        text = ""
    except sr.RequestError:
        print("⚠️ Speech recognition API unavailable.")
        text = ""

    return (text, round(avg_volume, 4)) if get_volume else text


def test_audio_system():
    """
    Quick helper to test both speaking and recording.
    """
    speak("Hello. This is a quick mic and speaker test. Please say a short sentence after the beep.")
    time.sleep(0.3)
    print("Please speak now...")
    result = record_answer(duration=5, get_volume=True)
    if isinstance(result, tuple):
        text, vol = result
    else:
        text = result
        vol = 0.0
    print("Detected text:", text)
    print("Average volume:", vol)
    if text:
        speak(f"You said: {text}")
    else:
        speak("I could not hear you clearly. Please check your microphone.")
