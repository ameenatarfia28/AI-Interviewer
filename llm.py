import json

import streamlit as st
from google import genai

from config import GEMINI_MODEL, get_gemini_api_key


client = genai.Client(api_key=get_gemini_api_key())


QUESTION_POOL_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "topic": {"type": "string"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["Easy", "Medium", "Hard"]
                    }
                },
                "required": ["question", "topic", "difficulty"]
            }
        }
    },
    "required": ["questions"]
}


EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
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
    "required": ["score", "feedback", "strengths", "improvements"]
}



def _extract_json(text):
    """Parse a JSON response with a small fallback for fenced JSON."""
    if not text:
        raise ValueError("Gemini returned an empty response.")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    return json.loads(cleaned)



def _clean_questions(data):
    result = []

    for item in data.get("questions", []):
        question = str(item.get("question", "")).strip()
        topic = str(item.get("topic", "General")).strip()
        difficulty = str(item.get("difficulty", "Medium")).title().strip()

        if not question:
            continue

        if difficulty not in {"Easy", "Medium", "Hard"}:
            difficulty = "Medium"

        result.append({
            "question": question,
            "topic": topic,
            "difficulty": difficulty
        })

    return result


@st.cache_data(ttl=3600, show_spinner=False)
def generate_question_pool(subject, selected_topics, total_questions, starting_difficulty="Medium"):
    """
    Generate a reusable pool in one Gemini request.

    The application then selects from this pool locally, avoiding a
    Gemini request every time the user clicks Next Question.
    """
    topics = [str(topic) for topic in selected_topics]
    requested = max(1, int(total_questions))

    # Generate more than the visible interview length so adaptive
    # selection has alternatives across difficulty levels.
    pool_size = min(max(requested * 2, 6), 18)

    prompt = f"""
You are an interview-question generator for an AI technical interview platform.

Subject: {subject}
Topics: {', '.join(topics)}
Starting difficulty: {starting_difficulty}

Generate exactly {pool_size} concise interview questions.
Create a balanced pool containing Easy, Medium, and Hard questions so a local
adaptive engine can choose the next question without another API request.
Distribute questions across the selected topics as evenly as practical.

Rules:
- Technical interview questions only.
- Do not provide answers.
- Avoid duplicate or near-duplicate questions.
- Questions should be suitable for a student/early-career candidate.
- Return only the requested JSON structure.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": QUESTION_POOL_SCHEMA,
        },
    )

    data = _extract_json(response.text)
    questions = _clean_questions(data)

    if not questions:
        raise RuntimeError("Gemini did not return usable interview questions.")

    return questions



def generate_question(subject, topic, difficulty, previous_question=None, previous_feedback=None):
    """
    Backward-compatible single-question function.

    New app flow should prefer generate_question_pool().
    """
    prompt = f"""
Generate ONE concise technical interview question.
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}
Do not give the answer. Return only the question text.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return response.text.strip()



def evaluate_answer(question, answer, subject):
    """Evaluate a typed/transcribed answer using structured JSON."""
    prompt = f"""
You are a technical interviewer.

Subject: {subject}
Question: {question}
Candidate answer: {answer}

Evaluate only the candidate's actual answer.

Scoring guide:
- 9-10: excellent, technically accurate and complete
- 7-8: good, mostly correct with minor gaps
- 5-6: partially correct but important gaps exist
- 3-4: weak understanding or major errors
- 0-2: incorrect, irrelevant, or no meaningful answer

Return JSON only with:
score: integer from 0 to 10
feedback: concise explanation
strengths: list of strengths
improvements: list of improvements
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": EVALUATION_SCHEMA,
        },
    )

    data = _extract_json(response.text)
    score = max(0, min(10, int(data.get("score", 0))))
    feedback = str(data.get("feedback", "")).strip()
    strengths = [str(x) for x in data.get("strengths", [])]
    improvements = [str(x) for x in data.get("improvements", [])]

    return {
        "score": score,
        "feedback": feedback,
        "strengths": strengths,
        "improvements": improvements,
        "raw": data,
    }



def format_evaluation(evaluation):
    """Create readable markdown for the Streamlit UI."""
    lines = [evaluation.get("feedback", "")]

    strengths = evaluation.get("strengths", [])
    improvements = evaluation.get("improvements", [])

    if strengths:
        lines.append("\n**Strengths**")
        lines.extend(f"- {item}" for item in strengths)

    if improvements:
        lines.append("\n**Improvements**")
        lines.extend(f"- {item}" for item in improvements)

    lines.append(f"\n**Score: {evaluation.get('score', 0)}/10**")

    return "\n".join(lines)