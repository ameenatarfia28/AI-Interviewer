import os
import io
import wave
import struct
import math

from google import genai


# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =========================================================
# SILENCE DETECTION
# =========================================================

def is_silent_audio(audio_bytes, silence_threshold=500):
    """
    Checks whether the recorded WAV audio contains
    meaningful sound.

    Returns:
        True  -> Audio is silent / almost silent
        False -> Audio contains sound
    """

    try:
        audio_stream = io.BytesIO(audio_bytes)

        with wave.open(audio_stream, "rb") as wav_file:

            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()

            raw_audio = wav_file.readframes(frame_count)

        # -------------------------------------------------
        # No audio data
        # -------------------------------------------------

        if not raw_audio:
            return True

        # -------------------------------------------------
        # 16-bit PCM
        # -------------------------------------------------

        if sample_width == 2:

            sample_count = len(raw_audio) // 2

            samples = struct.unpack(
                f"<{sample_count}h",
                raw_audio
            )

        # -------------------------------------------------
        # 8-bit PCM
        # -------------------------------------------------

        elif sample_width == 1:

            samples = [
                sample - 128
                for sample in raw_audio
            ]

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

            # Unknown audio format
            # Let Gemini handle it
            return False

        # -------------------------------------------------
        # No samples
        # -------------------------------------------------

        if not samples:
            return True

        # -------------------------------------------------
        # Calculate RMS audio energy
        # -------------------------------------------------

        squared_sum = sum(
            sample * sample
            for sample in samples
        )

        rms = math.sqrt(
            squared_sum / len(samples)
        )

        print(f"Audio RMS: {rms}")

        # -------------------------------------------------
        # Determine silence
        # -------------------------------------------------

        return rms < silence_threshold

    except Exception as e:

        print(
            f"Silence detection error: {e}"
        )

        # If local audio analysis fails,
        # don't automatically reject the recording.
        return False


# =========================================================
# TRANSCRIBE AUDIO
# =========================================================

def transcribe_audio(
    audio_bytes,
    mime_type="audio/wav"
):
    """
    Converts the candidate's voice recording into text.

    The function first checks for silence locally.
    If speech is present, Gemini transcribes the audio.

    Returns:
        str -> transcript

    Raises:
        ValueError("NO_SPEECH_DETECTED")
        when no meaningful speech is detected.
    """

    # =====================================================
    # BASIC VALIDATION
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
    # TRANSCRIPTION PROMPT
    # =====================================================

    prompt = """
You are a strict speech-to-text system for an AI technical
interview application.

Your job is ONLY to transcribe what the candidate actually says.

IMPORTANT RULES:

1. NEVER invent or hallucinate an answer.
2. NEVER guess what the candidate intended to say.
3. NEVER create a dummy/sample answer.
4. NEVER answer the interview question yourself.
5. NEVER summarize the candidate's answer.
6. Do not add explanations.
7. Preserve technical terminology exactly when possible.
8. If the candidate says nothing, return exactly:
   NO_SPEECH_DETECTED
9. If there is only silence, return exactly:
   NO_SPEECH_DETECTED
10. If there is only background noise and no understandable speech,
    return exactly:
    NO_SPEECH_DETECTED
11. If the candidate speaks only a few words, return only those
    words.
12. Do not complete an incomplete sentence yourself.

Return ONLY one of these:

- The exact transcript of the candidate's speech
OR
- NO_SPEECH_DETECTED
"""

    # =====================================================
    # SEND AUDIO TO GEMINI
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
                    "data": audio_bytes,
                    "mime_type": mime_type
                }
            ]
        )

    except Exception as e:

        print(
            f"Gemini transcription error: {e}"
        )

        raise e

    # =====================================================
    # GET GEMINI RESPONSE
    # =====================================================

    transcript = interaction.output_text.strip()

    # =====================================================
    # EMPTY RESPONSE
    # =====================================================

    if not transcript:

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # GEMINI DETECTED NO SPEECH
    # =====================================================

    if transcript.upper().strip() == "NO_SPEECH_DETECTED":

        raise ValueError(
            "NO_SPEECH_DETECTED"
        )

    # =====================================================
    # EXTRA PROTECTION AGAINST GENERATED RESPONSES
    # =====================================================

    fake_responses = [

        "there is no speech",

        "no speech detected",

        "the speaker did not say anything",

        "the audio is silent",

        "the audio contains silence",

        "no audible speech",

        "the candidate did not speak",

        "the candidate has not spoken",

        "there is no audible speech",

        "no understandable speech"
    ]

    transcript_lower = transcript.lower().strip()

    for phrase in fake_responses:

        if transcript_lower == phrase:

            raise ValueError(
                "NO_SPEECH_DETECTED"
            )

    # =====================================================
    # RETURN REAL TRANSCRIPT
    # =====================================================

    return transcript