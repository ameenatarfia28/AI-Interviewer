from google import genai

from config import GEMINI_API_KEY


client = genai.Client(
    api_key=GEMINI_API_KEY
)


MODEL_NAME = "gemini-3.6-flash"


def analyze_resume(resume_text):

    prompt = f"""
You are an expert technical recruiter.

Analyze the following candidate resume.

Resume:
{resume_text}

Extract the following:

1. Technical skills
2. Programming languages
3. Frameworks and libraries
4. Tools and technologies
5. Projects
6. Project technologies
7. Areas of expertise
8. Potential technical interview topics

Return the result in a clear structured format.
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text.strip()
def analyze_job_description(job_description):

    prompt = f"""
You are an expert technical recruiter.

Analyze the following job description.

Job Description:
{job_description}

Extract:

1. Required technical skills
2. Programming languages
3. Frameworks
4. Tools
5. Important concepts
6. Expected responsibilities
7. Technical interview topics

Return the result in a clear structured format.
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text.strip()
def match_resume_with_job(
    resume_analysis,
    job_analysis
):

    prompt = f"""
You are an expert technical recruiter.

Compare the candidate resume with the job description.

CANDIDATE RESUME ANALYSIS:
{resume_analysis}

JOB DESCRIPTION ANALYSIS:
{job_analysis}

Identify:

1. Matching skills
2. Missing skills
3. Strong areas
4. Weak areas
5. Relevant projects
6. Recommended interview topics
7. Recommended difficulty level

Return a structured analysis.
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text.strip()