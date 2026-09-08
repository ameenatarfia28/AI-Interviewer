import os
import io
import wave
import struct
import math
import base64

from google import genai


# =========================================================
# GEMINI CLIENT
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured."
    )

client = genai.Client(
    api_key=API_KEY
)


# =========================================================
# SILENCE DETECTION
# =========================================================

def is_silent_audio(
    audio_bytes,
    silence_threshold=500
):
    """
    Check whether a WAV recording is essentially silent.

    Returns:
        True  -> no meaningful audio detected
        False -> audio/speech may be present
    """

    if not audio_bytes:
        return True

    try:

        audio_stream = io.BytesIO(audio_bytes)

        with wave.open(audio_stream, "rb") as wav_file:

            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()

            raw_audio = wav_file.readframes(
                frame_count
            )

        if not raw_audio:
            return True

        # -------------------------------------------------
        # 8-bit PCM
        # -------------------------------------------------

        if sample_width == 1:

            samples = [
                sample - 128
                for sample in raw_audio
            ]

        # -------------------------------------------------
        # 16-bit PCM
        # -------------------------------------------------

        elif sample_width == 2:

            sample_count = len(raw_audio) // 2

            samples = struct.unpack(
                f"<{sample_count}h",
                raw_audio
            )

        # -------------------------------------------------
        # 32-bit PCM
        # -------------------------------------------------

        elif sample_width == 4:

            sample_count = len(raw_audio) // 4

            samples = struct.unpack(
                f"<{sample_count}i",
                raw_audio
            )

        else:

            # Unknown WAV format.
            # Let Gemini process it.
            return False

        if not samples:
            return True

        # -------------------------------------------------
        # RMS energy
        # -------------------------------------------------

        squared_sum = sum(
            sample * sample
            for sample in samples
        )

        rms = math.sqrt(
            squared_sum / len(samples)
        )

        print(
            f"[VOICE] Audio RMS: {rms:.2f}"
        )

        return rms < silence_threshold

    except Exception as e:

        print(
            f"[VOICE] Silence detection warning: {e}"
        )

        # Don't reject valid recordings just because
        # local silence analysis failed.
        return False


# =========================================================
# TRANSCRIBE AUDIO
# =========================================================

def transcribe_audio(
    audio_bytes,
    mime_type="audio/wav"
):
    """
    Convert the candidate's speech into text.

    Important:
    Gemini expects inline audio `data` as a Base64 string,
    not raw binary bytes.
    """

    # =====================================================
    # VALIDATE AUDIO
    # =====================================================

    if not audio_bytes:

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # LOCAL SILENCE CHECK
    # =====================================================

    if is_silent_audio(audio_bytes):

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # CONVERT BINARY AUDIO -> BASE64 STRING
    # =====================================================

    audio_base64 = base64.b64encode(
        audio_bytes
    ).decode("utf-8")

    # =====================================================
    # TRANSCRIPTION PROMPT
    # =====================================================

    prompt = """
You are a strict speech-to-text system for a technical
interview application.

Your ONLY task is to transcribe the candidate's actual speech.

Rules:

1. Never invent words.
2. Never guess what the candidate intended to say.
3. Never create a dummy answer.
4. Never answer the interview question yourself.
5. Never summarize the candidate's response.
6. Do not add explanations.
7. Preserve technical terms such as Python, Java, SQL,
   OOP, API, database, machine learning, etc.
8. If the candidate says nothing, return exactly:
   NO_SPEECH_DETECTED
9. If the recording contains only silence, return exactly:
   NO_SPEECH_DETECTED
10. If there is only background noise and no understandable
    speech, return exactly:
    NO_SPEECH_DETECTED
11. If the candidate says only a few words, return only those
    words.
12. Do not complete incomplete sentences yourself.

Return ONLY:

The actual transcript

OR

NO_SPEECH_DETECTED
"""

    # =====================================================
    # GEMINI REQUEST
    # =====================================================

    try:

        interaction = client.interactions.create(

            model="gemini-3.6-flash",

            input=[
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "audio",
                    "data": audio_base64,
                    "mime_type": mime_type
                }
            ]
        )

    except Exception as e:

        print(
            f"[VOICE] Gemini error: {e}"
        )

        raise e

    # =====================================================
    # GET OUTPUT
    # =====================================================

    transcript = (
        interaction.output_text or ""
    ).strip()

    # =====================================================
    # EMPTY RESPONSE
    # =====================================================

    if not transcript:

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # EXPLICIT NO-SPEECH RESPONSE
    # =====================================================

    if transcript.upper() == "NO_SPEECH_DETECTED":

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # PROTECT AGAINST NON-TRANSCRIPT RESPONSES
    # =====================================================

    invalid_responses = {

        "there is no speech",
        "no speech detected",
        "no audible speech",
        "the audio is silent",
        "the audio contains silence",
        "the speaker did not say anything",
        "the candidate did not speak",
        "the candidate has not spoken",
        "no understandable speech"
    }

    normalized = transcript.lower().strip()

    if normalized in invalid_responses:

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # RETURN REAL TRANSCRIPT
    # =====================================================

    print(
        f"[VOICE] Transcript: {transcript}"
    )

    return transcript