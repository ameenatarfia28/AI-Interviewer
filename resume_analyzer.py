import json

import streamlit as st
from google import genai

from config import GEMINI_MODEL, get_gemini_api_key
from llm import _extract_json, QUESTION_POOL_SCHEMA


client = genai.Client(api_key=get_gemini_api_key())


RESUME_JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "resume_summary": {"type": "string"},
        "job_summary": {"type": "string"},
        "match_summary": {"type": "string"},
        "matched_skills": {
            "type": "array",
            "items": {"type": "string"}
        },
        "missing_skills": {
            "type": "array",
            "items": {"type": "string"}
        },
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
    "required": [
        "resume_summary",
        "job_summary",
        "match_summary",
        "matched_skills",
        "missing_skills",
        "questions"
    ]
}


@st.cache_data(ttl=3600, show_spinner=False)
def analyze_resume_job(resume_text, job_description, total_questions=5):
    """Perform resume analysis, JD analysis, matching, and question generation in one request."""
    resume_text = str(resume_text)[:25000]
    job_description = str(job_description)[:15000]

    pool_size = min(max(int(total_questions) * 2, 6), 18)

    prompt = f"""
You are an AI interview-preparation assistant.

Analyze the candidate resume and job description below in ONE pass.
Then generate a reusable question pool of exactly {pool_size} interview questions.
The questions should be personalized to the candidate's background and the job.
Use Easy, Medium, and Hard difficulty labels.

Return:
1. concise resume summary
2. concise job summary
3. concise resume-to-job match summary
4. matched skills
5. missing/less-evident skills
6. personalized interview questions

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Do not invent facts that are not supported by the supplied resume/JD.
Return JSON only.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": RESUME_JOB_SCHEMA,
        },
    )

    data = _extract_json(response.text)

    questions = []
    for item in data.get("questions", []):
        question = str(item.get("question", "")).strip()
        topic = str(item.get("topic", "Resume/JD")).strip()
        difficulty = str(item.get("difficulty", "Medium")).title()
        if question:
            if difficulty not in {"Easy", "Medium", "Hard"}:
                difficulty = "Medium"
            questions.append({
                "question": question,
                "topic": topic,
                "difficulty": difficulty,
            })

    if not questions:
        raise RuntimeError(
            "Gemini did not return personalized interview questions."
        )

    return {
        "resume_summary": str(data.get("resume_summary", "")),
        "job_summary": str(data.get("job_summary", "")),
        "match_summary": str(data.get("match_summary", "")),
        "matched_skills": [str(x) for x in data.get("matched_skills", [])],
        "missing_skills": [str(x) for x in data.get("missing_skills", [])],
        "questions": questions,
    }


# ---------------------------------------------------------
# Compatibility wrappers for your existing code
# ---------------------------------------------------------


def analyze_resume(resume_text):
    return resume_text



def analyze_job_description(job_description):
    return job_description



def match_resume_with_job(resume_analysis, job_analysis):
    return "Use analyze_resume_job() for the combined optimized analysis."
