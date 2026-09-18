import io
import math
import struct
import wave

from google import genai
from google.genai import types

from config import GEMINI_MODEL, get_gemini_api_key
from llm import _extract_json


client = genai.Client(api_key=get_gemini_api_key())


VOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "speech_detected": {"type": "boolean"},
        "transcript": {"type": "string"},
        "score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10
        },
        "feedback": {"type": "string"},
        "strengths": {
            "type": "array",
            "items": {"type": "string"}
        },
        "improvements": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "speech_detected",
        "transcript",
        "score",
        "feedback",
        "strengths",
        "improvements"
    ]
}



def is_silent_audio(audio_bytes, silence_threshold=350):
    """Fast local RMS check to reject recordings with no meaningful sound."""
    if not audio_bytes:
        return True

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            sample_width = wav_file.getsampwidth()
            frame_count = wav_file.getnframes()
            raw_audio = wav_file.readframes(frame_count)

        if not raw_audio:
            return True

        if sample_width == 1:
            samples = [sample - 128 for sample in raw_audio]
        elif sample_width == 2:
            count = len(raw_audio) // 2
            samples = struct.unpack(f"<{count}h", raw_audio)
        elif sample_width == 4:
            count = len(raw_audio) // 4
            samples = struct.unpack(f"<{count}i", raw_audio)
        else:
            return False

        if not samples:
            return True

        rms = math.sqrt(
            sum(sample * sample for sample in samples) / len(samples)
        )

        print(f"[VOICE] Audio RMS: {rms:.2f}")
        return rms < silence_threshold

    except Exception as exc:
        print(f"[VOICE] Silence-check warning: {exc}")
        return False



def analyze_voice_answer(audio_bytes, mime_type, question, subject):
    """
    ONE Gemini request for:
    audio -> speech detection + transcript + score + feedback.
    """
    if not audio_bytes or is_silent_audio(audio_bytes):
        raise ValueError("NO_SPEECH_DETECTED")

    prompt = f"""
You are a strict AI technical interviewer.

Subject: {subject}
Question asked: {question}

Listen to the candidate's audio and return a structured evaluation.

Rules for transcription:
- Transcribe only what the candidate actually says.
- Never invent words or complete missing sentences.
- Never answer the interview question yourself.
- If there is no understandable speech, set speech_detected=false,
  transcript="", score=0.

Rules for evaluation:
- Evaluate only the spoken answer.
- Give a score from 0 to 10.
- Consider technical correctness, relevance, completeness, and clarity.
- Keep feedback concise and useful.

Return JSON only.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type or "audio/wav",
                ),
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": VOICE_SCHEMA,
            },
        )
    except Exception as exc:
        raise exc

    data = _extract_json(response.text)

    speech_detected = bool(data.get("speech_detected", False))
    transcript = str(data.get("transcript", "")).strip()

    if not speech_detected or not transcript:
        raise ValueError("NO_SPEECH_DETECTED")

    score = max(0, min(10, int(data.get("score", 0))))

    return {
        "speech_detected": True,
        "transcript": transcript,
        "score": score,
        "feedback": str(data.get("feedback", "")).strip(),
        "strengths": [str(x) for x in data.get("strengths", [])],
        "improvements": [str(x) for x in data.get("improvements", [])],
    }


# Backward-compatible name. The optimized app calls analyze_voice_answer().
def transcribe_audio(audio_bytes, mime_type="audio/wav"):
    """Transcribe-only helper kept for compatibility."""
    if not audio_bytes or is_silent_audio(audio_bytes):
        raise ValueError("NO_SPEECH_DETECTED")

    prompt = """
Transcribe ONLY the candidate's actual speech.
Never invent words.
If no understandable speech is present, return exactly NO_SPEECH_DETECTED.
Return only the transcript text.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type=mime_type or "audio/wav",
            ),
        ],
    )

    transcript = (response.text or "").strip()

    if not transcript or transcript.upper() == "NO_SPEECH_DETECTED":
        raise ValueError("NO_SPEECH_DETECTED")

    return transcript