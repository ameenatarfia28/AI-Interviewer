from google import genai

from config import GEMINI_API_KEY
from prompts import (
    question_generation_prompt,
    answer_evaluation_prompt
)


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# GENERATE INTERVIEW QUESTION
# ============================================================

def generate_question(
    subject,
    topic,
    difficulty,
    previous_question=None,
    previous_feedback=None,
    resume_context=None,
    job_context=None
):

    prompt = question_generation_prompt(
        subject,
        topic,
        difficulty,
        previous_question,
        previous_feedback,
        resume_context,
        job_context
    )

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text.strip()


# ============================================================
# EVALUATE CANDIDATE ANSWER
# ============================================================

def evaluate_answer(
    question,
    answer,
    subject
):
    """
    Evaluate the candidate's answer using Gemini.
    """

    prompt = answer_evaluation_prompt(
        question,
        answer,
        subject
    )

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text.strip()