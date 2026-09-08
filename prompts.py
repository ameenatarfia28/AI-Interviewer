def question_generation_prompt(
    subject,
    topic,
    difficulty,
    previous_question=None,
    previous_feedback=None,
    resume_context=None,
    job_context=None
):

    context = ""

    if previous_question:

        context += f"""
Previous Question:
{previous_question}
"""

    if previous_feedback:

        context += f"""
Previous Evaluation:
{previous_feedback}
"""

    if resume_context:

        context += f"""
Candidate Resume Information:
{resume_context}
"""

    if job_context:

        context += f"""
Job Description Information:
{job_context}
"""

    return f"""
You are an experienced technical interviewer.

Generate ONE personalized technical interview question.

Subject:
{subject}

Topic:
{topic}

Difficulty:
{difficulty}

{context}

Requirements:

- The question must test the requested topic.
- Match the requested difficulty.
- Use the candidate's resume when relevant.
- Prefer questions related to the candidate's projects
  and technologies.
- If a job description is provided, prioritize skills
  relevant to that job.
- Do not repeat the previous question.
- If the previous answer was weak, test that concept again.
- If the previous answer was strong, increase the challenge.
- Do not provide the answer.
- Do not provide hints.

Return ONLY the interview question.
"""


def answer_evaluation_prompt(question, answer, subject):
    return f"""
You are an experienced technical interviewer evaluating a candidate.

Subject: {subject}

Interview Question:
{question}

Candidate's Answer:
{answer}

Evaluate the candidate's answer.

Give a score from 0 to 10.

Consider:
1. Correctness
2. Relevance
3. Completeness
4. Technical understanding

Return your response in exactly this format:

SCORE: <number>

FEEDBACK:
<short explanation of how good the answer is>

MISSING_CONCEPTS:
<important concepts the candidate missed, or "None">

IMPROVEMENT:
<one or two suggestions to improve the answer>
"""