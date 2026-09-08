import streamlit as st
import html
import re

from llm import generate_question, evaluate_answer

from adaptive_engine import (
    determine_next_difficulty,
    select_next_topic
)

from topics import SUBJECT_TOPICS

from resume_parser import extract_resume_text

from resume_analyzer import (
    analyze_resume,
    analyze_job_description,
    match_resume_with_job
)

from voice_engine import transcribe_audio


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Interviewer",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# PREMIUM DARK UI
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #080b12;
        color: #f5f7fb;
    }

    .main {
        padding: 2rem;
    }

    .hero {
        text-align: center;
        padding: 30px 10px;
    }

    .hero-title {
        font-size: 48px;
        font-weight: 800;
        margin-bottom: 10px;
        color: #ffffff;
    }

    .hero-subtitle {
        font-size: 18px;
        color: #9ca3af;
        margin-bottom: 25px;
    }

    .feature-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 24px;
        height: 100%;
    }

    .feature-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .feature-text {
        color: #9ca3af;
        line-height: 1.6;
    }

    .question-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 18px;
        padding: 28px;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .question-label {
        color: #60a5fa;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 10px;
    }

    .question-text {
        font-size: 22px;
        font-weight: 600;
        line-height: 1.5;
        color: #ffffff;
    }

    .feedback-card {
        background: #101827;
        border-left: 4px solid #60a5fa;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
    }

    .score-badge {
        background: #172554;
        color: #93c5fd;
        padding: 10px 18px;
        border-radius: 20px;
        font-size: 18px;
        font-weight: 700;
        display: inline-block;
        margin: 10px 0;
    }

    .transcript-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {

    # Topic interview
    "topic_started": False,
    "topic_question": None,
    "topic_answered": False,
    "topic_current_index": 0,
    "topic_current_topic": None,
    "topic_current_difficulty": "Medium",
    "topic_scores": {},
    "topic_history": [],
    "topic_subject": None,
    "topic_selected_topics": [],
    "topic_total_questions": 5,
    "topic_feedback": None,
    "topic_score": None,

    # Resume interview
    "resume_started": False,
    "resume_question": None,
    "resume_answered": False,
    "resume_current_index": 0,
    "resume_current_topic": None,
    "resume_current_difficulty": "Medium",
    "resume_scores": {},
    "resume_history": [],
    "resume_total_questions": 5,
    "resume_feedback": None,
    "resume_score": None,
    "resume_transcript": None,

    # Voice interview
    "voice_started": False,
    "voice_question": None,
    "voice_answered": False,
    "voice_current_index": 0,
    "voice_current_topic": None,
    "voice_current_difficulty": "Medium",
    "voice_scores": {},
    "voice_history": [],
    "voice_subject": None,
    "voice_selected_topics": [],
    "voice_total_questions": 5,
    "voice_feedback": None,
    "voice_score": None,
    "voice_transcript": None,
    "voice_audio": None
}


for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_score_from_feedback(feedback):

    if not feedback:
        return 0

    patterns = [
        r"Score\s*:\s*(\d+)",
        r"Score\s*-\s*(\d+)",
        r"(\d+)\s*/\s*10"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            feedback,
            re.IGNORECASE
        )

        if match:
            return int(match.group(1))

    return 0


def dynamic_message(score):

    if score >= 9:
        return "🔥 Excellent answer! You have strong understanding."

    elif score >= 7:
        return "👏 Good answer! You are on the right track."

    elif score >= 5:
        return "👍 Decent answer. Try adding more technical depth."

    else:
        return "💡 Keep practicing. Focus on the core concepts."


def question_card(question, number, difficulty):

    st.html(
        f"""
        <div class="question-card">

            <div class="question-label">
                QUESTION {number} • {html.escape(str(difficulty))}
            </div>

            <div class="question-text">
                {html.escape(str(question))}
            </div>

        </div>
        """
    )


def ai_feedback_card(feedback):

    safe_feedback = html.escape(
        str(feedback)
    )

    safe_feedback = safe_feedback.replace(
        "\n",
        "<br>"
    )

    st.html(
        f"""
        <div class="feedback-card">

            <h3>🤖 AI Feedback</h3>

            <div style="line-height:1.7;">
                {safe_feedback}
            </div>

        </div>
        """
    )


def score_badge(score):

    st.html(
        f"""
        <div class="score-badge">
            ⭐ Score: {score}/10
        </div>
        """
    )


def flatten_topic_scores(score_dict):
    """
    Converts:
        {"OOP": [8, 7], "Inheritance": [9]}

    into:
        [8, 7, 9]
    """

    all_scores = []

    for value in score_dict.values():

        if isinstance(value, list):
            all_scores.extend(value)

        elif isinstance(value, (int, float)):
            all_scores.append(value)

    return all_scores


# =========================================================
# HERO
# =========================================================

st.html(
    """
    <div class="hero">

        <div class="hero-title">
            🤖 AI Interviewer
        </div>

        <div class="hero-subtitle">
            Practice smarter. Get evaluated. Improve continuously.
        </div>

    </div>
    """
)


# =========================================================
# FEATURE CARDS
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.html(
        """
        <div class="feature-card">

            <div class="feature-title">
                🎯 Topic-Based
            </div>

            <div class="feature-text">
                Practice Python, Java, SQL, Machine Learning,
                DSA and other technical subjects.
            </div>

        </div>
        """
    )


with col2:

    st.html(
        """
        <div class="feature-card">

            <div class="feature-title">
                📄 Resume-Aware
            </div>

            <div class="feature-text">
                Upload your resume and job description
                to get personalized interview questions.
            </div>

        </div>
        """
    )


with col3:

    st.html(
        """
        <div class="feature-card">

            <div class="feature-title">
                🎙️ Voice Interview
            </div>

            <div class="feature-text">
                Answer interview questions using your voice
                and receive AI-powered feedback.
            </div>

        </div>
        """
    )


st.write("")


# =========================================================
# TABS
# =========================================================

topic_tab, resume_tab, voice_tab = st.tabs(
    [
        "🎯  Topic-Based Interview",
        "📄  Resume + Job Interview",
        "🎙️  Voice Interview"
    ]
)


# =========================================================
# TOPIC INTERVIEW
# =========================================================

with topic_tab:

    st.subheader("🎯 Topic-Based Interview")

    col1, col2 = st.columns(2)

    with col1:

        subject = st.selectbox(
            "Choose Subject",
            list(SUBJECT_TOPICS.keys()),
            key="topic_subject_select"
        )

        difficulty = st.selectbox(
            "Starting Difficulty",
            ["Easy", "Medium", "Hard"],
            key="topic_difficulty_select"
        )

    with col2:

        available_topics = SUBJECT_TOPICS[subject]

        selected_topics = st.multiselect(
            "Select Topics",
            available_topics,
            default=available_topics[:3],
            key="topic_selected_topics_select"
        )

        total_questions = st.number_input(
            "Number of Questions",
            min_value=1,
            max_value=20,
            value=5,
            key="topic_total_questions_input"
        )


    # -----------------------------------------------------
    # START TOPIC INTERVIEW
    # -----------------------------------------------------

    if not st.session_state.topic_started:

        if st.button(
            "🚀 Start Interview",
            key="start_topic_interview",
            use_container_width=True
        ):

            if not selected_topics:

                st.warning(
                    "Please select at least one topic."
                )

            else:

                first_topic = selected_topics[0]

                try:

                    with st.spinner(
                        "Generating your first question..."
                    ):

                        question = generate_question(
                            subject,
                            first_topic,
                            difficulty
                        )

                    st.session_state.topic_started = True
                    st.session_state.topic_question = question
                    st.session_state.topic_current_topic = first_topic
                    st.session_state.topic_current_difficulty = difficulty
                    st.session_state.topic_subject = subject
                    st.session_state.topic_selected_topics = selected_topics
                    st.session_state.topic_total_questions = total_questions
                    st.session_state.topic_current_index = 0

                    # Topic -> list of scores
                    st.session_state.topic_scores = {}

                    st.session_state.topic_history = []
                    st.session_state.topic_answered = False
                    st.session_state.topic_feedback = None
                    st.session_state.topic_score = None

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"❌ Could not start interview: {e}"
                    )


    # -----------------------------------------------------
    # ACTIVE TOPIC INTERVIEW
    # -----------------------------------------------------

    if st.session_state.topic_started:

        current_index = st.session_state.topic_current_index

        total_questions = st.session_state.topic_total_questions

        question = st.session_state.topic_question

        question_card(
            question,
            current_index + 1,
            st.session_state.topic_current_difficulty
        )


        if not st.session_state.topic_answered:

            answer = st.text_area(
                "Your Answer",
                height=180,
                key=f"topic_answer_{current_index}"
            )


            if st.button(
                "🤖 Evaluate Answer",
                key=f"evaluate_topic_{current_index}",
                use_container_width=True
            ):

                if not answer.strip():

                    st.warning(
                        "Please enter your answer."
                    )

                else:

                    try:

                        with st.spinner(
                            "🤖 Evaluating your answer..."
                        ):

                            feedback = evaluate_answer(
                                question,
                                answer,
                                st.session_state.topic_subject
                            )

                        score = get_score_from_feedback(
                            feedback
                        )

                        st.session_state.topic_feedback = feedback
                        st.session_state.topic_score = score

                        current_topic = (
                            st.session_state.topic_current_topic
                        )

                        if current_topic not in st.session_state.topic_scores:
                            st.session_state.topic_scores[current_topic] = []

                        st.session_state.topic_scores[
                            current_topic
                        ].append(score)

                        st.session_state.topic_history.append(
                            {
                                "question": question,
                                "topic": current_topic,
                                "answer": answer,
                                "score": score,
                                "feedback": feedback
                            }
                        )

                        st.session_state.topic_answered = True

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Evaluation failed: {e}"
                        )


        else:

            score_badge(
                st.session_state.topic_score
            )

            st.write(
                dynamic_message(
                    st.session_state.topic_score
                )
            )

            ai_feedback_card(
                st.session_state.topic_feedback
            )


            if current_index + 1 < total_questions:

                if st.button(
                    "➡️ Next Question",
                    key=f"next_topic_{current_index}",
                    use_container_width=True
                ):

                    try:

                        next_difficulty = (
                            determine_next_difficulty(
                                st.session_state.topic_score,
                                st.session_state.topic_current_difficulty
                            )
                        )

                        next_topic = select_next_topic(
                            st.session_state.topic_selected_topics,
                            st.session_state.topic_scores
                        )

                        with st.spinner(
                            "🧠 Creating your next adaptive question..."
                        ):

                            next_question = generate_question(
                                st.session_state.topic_subject,
                                next_topic,
                                next_difficulty
                            )

                        st.session_state.topic_current_index += 1

                        st.session_state.topic_current_topic = (
                            next_topic
                        )

                        st.session_state.topic_current_difficulty = (
                            next_difficulty
                        )

                        st.session_state.topic_question = (
                            next_question
                        )

                        st.session_state.topic_answered = False
                        st.session_state.topic_feedback = None
                        st.session_state.topic_score = None

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Could not generate next question: {e}"
                        )

            else:

                st.success(
                    "🎉 Topic interview completed!"
                )

                st.subheader(
                    "📊 Interview Report"
                )

                scores = flatten_topic_scores(
                    st.session_state.topic_scores
                )

                if scores:

                    average = (
                        sum(scores) / len(scores)
                    )

                    st.metric(
                        "Average Score",
                        f"{average:.1f}/10"
                    )

                    for i, score in enumerate(
                        scores,
                        start=1
                    ):

                        st.write(
                            f"Question {i}: ⭐ {score}/10"
                        )


# =========================================================
# RESUME INTERVIEW
# =========================================================

with resume_tab:

    st.subheader(
        "📄 Resume + Job Description Interview"
    )

    resume_file = st.file_uploader(
        "Upload Resume",
        type=["pdf"],
        key="resume_upload"
    )

    job_description = st.text_area(
        "Paste Job Description",
        height=180,
        key="job_description"
    )

    resume_total_questions = st.number_input(
        "Number of Questions",
        min_value=1,
        max_value=20,
        value=5,
        key="resume_questions_input"
    )


    # -----------------------------------------------------
    # START RESUME INTERVIEW
    # -----------------------------------------------------

    if not st.session_state.resume_started:

        if st.button(
            "🚀 Start Resume Interview",
            key="start_resume_interview",
            use_container_width=True
        ):

            if resume_file is None:

                st.warning(
                    "Please upload your resume."
                )

            elif not job_description.strip():

                st.warning(
                    "Please enter the job description."
                )

            else:

                try:

                    with st.spinner(
                        "Analyzing resume and job description..."
                    ):

                        resume_text = extract_resume_text(
                            resume_file
                        )

                        resume_analysis = analyze_resume(
                            resume_text
                        )

                        job_analysis = analyze_job_description(
                            job_description
                        )

                        match_result = match_resume_with_job(
                            resume_analysis,
                            job_analysis
                        )

                        first_topic = "General Interview"

                        question = generate_question(
                            "Technical Interview",
                            first_topic,
                            "Medium"
                        )

                    st.session_state.resume_started = True
                    st.session_state.resume_question = question
                    st.session_state.resume_current_topic = first_topic
                    st.session_state.resume_current_difficulty = "Medium"
                    st.session_state.resume_total_questions = resume_total_questions
                    st.session_state.resume_current_index = 0
                    st.session_state.resume_scores = {}
                    st.session_state.resume_history = []
                    st.session_state.resume_answered = False
                    st.session_state.resume_feedback = None
                    st.session_state.resume_score = None

                    st.rerun()

                except Exception as e:

                    error_message = str(e)

                    if (
                        "429" in error_message
                        or "quota" in error_message.lower()
                        or "rate limit" in error_message.lower()
                    ):

                        st.error(
                            "⚠️ Gemini API quota has been exceeded. "
                            "Please wait and try again."
                        )

                    else:

                        st.error(
                            f"❌ Resume interview could not start: "
                            f"{error_message}"
                        )


    # -----------------------------------------------------
    # ACTIVE RESUME INTERVIEW
    # -----------------------------------------------------

    if st.session_state.resume_started:

        current_index = (
            st.session_state.resume_current_index
        )

        total_questions = (
            st.session_state.resume_total_questions
        )

        question = (
            st.session_state.resume_question
        )

        question_card(
            question,
            current_index + 1,
            st.session_state.resume_current_difficulty
        )


        if not st.session_state.resume_answered:

            answer = st.text_area(
                "Your Answer",
                height=180,
                key=f"resume_answer_{current_index}"
            )


            if st.button(
                "🤖 Evaluate Answer",
                key=f"evaluate_resume_{current_index}",
                use_container_width=True
            ):

                if not answer.strip():

                    st.warning(
                        "Please enter your answer."
                    )

                else:

                    try:

                        feedback = evaluate_answer(
                            question,
                            answer,
                            "Technical Interview"
                        )

                        score = get_score_from_feedback(
                            feedback
                        )

                        st.session_state.resume_feedback = feedback
                        st.session_state.resume_score = score

                        st.session_state.resume_scores[
                            current_index
                        ] = score

                        st.session_state.resume_history.append(
                            {
                                "question": question,
                                "answer": answer,
                                "score": score,
                                "feedback": feedback
                            }
                        )

                        st.session_state.resume_answered = True

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Evaluation failed: {e}"
                        )


        else:

            score_badge(
                st.session_state.resume_score
            )

            ai_feedback_card(
                st.session_state.resume_feedback
            )


            if current_index + 1 < total_questions:

                if st.button(
                    "➡️ Next Question",
                    key=f"next_resume_{current_index}",
                    use_container_width=True
                ):

                    try:

                        next_difficulty = (
                            determine_next_difficulty(
                                st.session_state.resume_score,
                                st.session_state.resume_current_difficulty
                            )
                        )

                        with st.spinner(
                            "🧠 Creating your next question..."
                        ):

                            next_question = generate_question(
                                "Technical Interview",
                                "General Interview",
                                next_difficulty
                            )

                        st.session_state.resume_current_index += 1

                        st.session_state.resume_current_difficulty = (
                            next_difficulty
                        )

                        st.session_state.resume_question = (
                            next_question
                        )

                        st.session_state.resume_answered = False
                        st.session_state.resume_feedback = None
                        st.session_state.resume_score = None

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"❌ Could not generate next question: {e}"
                        )

            else:

                st.success(
                    "🎉 Resume interview completed!"
                )

                scores = list(
                    st.session_state.resume_scores.values()
                )

                if scores:

                    average = (
                        sum(scores) / len(scores)
                    )

                    st.metric(
                        "Average Score",
                        f"{average:.1f}/10"
                    )


# =========================================================
# VOICE INTERVIEW
# =========================================================

with voice_tab:

    st.subheader(
        "🎙️ Voice Interview"
    )

    st.write(
        "Answer interview questions using your voice. "
        "Gemini will convert your speech into text and "
        "evaluate your answer."
    )


    # -----------------------------------------------------
    # VOICE SETUP
    # -----------------------------------------------------

    if not st.session_state.voice_started:

        col1, col2 = st.columns(2)

        with col1:

            voice_subject = st.selectbox(
                "Choose Subject",
                list(SUBJECT_TOPICS.keys()),
                key="voice_subject_select"
            )

            voice_difficulty = st.selectbox(
                "Starting Difficulty",
                ["Easy", "Medium", "Hard"],
                index=1,
                key="voice_difficulty_select"
            )


        with col2:

            voice_available_topics = (
                SUBJECT_TOPICS[voice_subject]
            )

            voice_selected_topics = st.multiselect(
                "Select Topics",
                voice_available_topics,
                default=voice_available_topics[:3],
                key="voice_selected_topics_select"
            )

            voice_total_questions = st.number_input(
                "Number of Questions",
                min_value=1,
                max_value=20,
                value=5,
                key="voice_total_questions_input"
            )


        # -------------------------------------------------
        # START VOICE INTERVIEW
        # -------------------------------------------------

        if st.button(
            "🎙️ Start Voice Interview",
            key="start_voice_interview",
            use_container_width=True
        ):

            if not voice_selected_topics:

                st.warning(
                    "Please select at least one topic."
                )

            else:

                first_topic = voice_selected_topics[0]

                try:

                    with st.spinner(
                        "Generating your first question..."
                    ):

                        question = generate_question(
                            voice_subject,
                            first_topic,
                            voice_difficulty
                        )


                    st.session_state.voice_started = True

                    st.session_state.voice_question = question

                    st.session_state.voice_subject = (
                        voice_subject
                    )

                    st.session_state.voice_selected_topics = (
                        voice_selected_topics
                    )

                    st.session_state.voice_current_topic = (
                        first_topic
                    )

                    st.session_state.voice_current_difficulty = (
                        voice_difficulty
                    )

                    st.session_state.voice_total_questions = (
                        voice_total_questions
                    )

                    st.session_state.voice_current_index = 0

                    # IMPORTANT:
                    # topic -> list of scores
                    st.session_state.voice_scores = {}

                    st.session_state.voice_history = []

                    st.session_state.voice_answered = False

                    st.session_state.voice_feedback = None

                    st.session_state.voice_score = None

                    st.session_state.voice_transcript = None

                    st.session_state.voice_audio = None

                    st.rerun()

                except Exception as e:

                    error_message = str(e)

                    if (
                        "429" in error_message
                        or "quota" in error_message.lower()
                        or "rate limit" in error_message.lower()
                    ):

                        st.error(
                            "⚠️ Gemini API quota has been exceeded. "
                            "Please wait and try again."
                        )

                    else:

                        st.error(
                            f"❌ Could not start voice interview: "
                            f"{error_message}"
                        )


    # -----------------------------------------------------
    # ACTIVE VOICE INTERVIEW
    # -----------------------------------------------------

    if st.session_state.voice_started:

        current_index = (
            st.session_state.voice_current_index
        )

        total_questions = (
            st.session_state.voice_total_questions
        )

        question = (
            st.session_state.voice_question
        )


        question_card(
            question,
            current_index + 1,
            st.session_state.voice_current_difficulty
        )


        # =================================================
        # RECORD ANSWER
        # =================================================

        if not st.session_state.voice_answered:

            st.markdown(
                "### 🎙️ Record Your Answer"
            )

            st.info(
                "Click the microphone button and speak "
                "your answer clearly."
            )


            audio_value = st.audio_input(
                "🎙️ Record your answer",
                key=f"voice_record_{current_index}"
            )


            if audio_value is not None:

                st.session_state.voice_audio = audio_value

                st.audio(
                    audio_value,
                    format="audio/wav"
                )

                st.success(
                    "✅ Voice recording captured!"
                )


                # -----------------------------------------
                # ANALYZE BUTTON
                # -----------------------------------------

                if st.button(
                    "🤖 Analyze Voice Answer",
                    key=f"analyze_voice_{current_index}",
                    use_container_width=True
                ):

                    try:

                        # ---------------------------------
                        # SPEECH TO TEXT
                        # ---------------------------------

                        with st.spinner(
                            "🎙️ Checking your recording..."
                        ):

                            audio_bytes = (
                                audio_value.getvalue()
                            )

                            mime_type = (
                                audio_value.type
                                or "audio/wav"
                            )

                            transcript = transcribe_audio(
                                audio_bytes,
                                mime_type
                            )


                        # ---------------------------------
                        # IMPORTANT:
                        # If there is no speech,
                        # transcribe_audio raises:
                        # NO_SPEECH_DETECTED
                        # ---------------------------------

                        if not transcript or not transcript.strip():

                            raise ValueError(
                                "NO_SPEECH_DETECTED"
                            )


                        st.session_state.voice_transcript = (
                            transcript
                        )


                        # ---------------------------------
                        # AI EVALUATION
                        # ---------------------------------

                        with st.spinner(
                            "🤖 AI is evaluating your answer..."
                        ):

                            feedback = evaluate_answer(
                                question,
                                transcript,
                                st.session_state.voice_subject
                            )


                        score = get_score_from_feedback(
                            feedback
                        )


                        st.session_state.voice_feedback = (
                            feedback
                        )

                        st.session_state.voice_score = (
                            score
                        )


                        # ---------------------------------
                        # STORE SCORE BY TOPIC
                        # ---------------------------------

                        current_topic = (
                            st.session_state.voice_current_topic
                        )


                        if current_topic not in (
                            st.session_state.voice_scores
                        ):

                            st.session_state.voice_scores[
                                current_topic
                            ] = []


                        st.session_state.voice_scores[
                            current_topic
                        ].append(score)


                        # ---------------------------------
                        # SAVE HISTORY
                        # ---------------------------------

                        st.session_state.voice_history.append(
                            {
                                "question": question,
                                "topic": current_topic,
                                "transcript": transcript,
                                "score": score,
                                "feedback": feedback
                            }
                        )


                        # ---------------------------------
                        # MARK AS ANSWERED
                        # ---------------------------------

                        st.session_state.voice_answered = True

                        st.rerun()


                    # =====================================
                    # NO SPEECH ERROR
                    # =====================================

                    except ValueError as e:

                        if str(e) == "NO_SPEECH_DETECTED":

                            st.warning(
                                "🎙️ No speech was detected in your "
                                "recording. Please record your answer "
                                "again and speak clearly."
                            )

                            st.session_state.voice_answered = False

                            st.session_state.voice_transcript = None

                        else:

                            st.error(
                                f"❌ {str(e)}"
                            )


                    # =====================================
                    # OTHER ERRORS
                    # =====================================

                    except Exception as e:

                        error_message = str(e)

                        if (
                            "429" in error_message
                            or "quota" in error_message.lower()
                            or "rate limit" in error_message.lower()
                        ):

                            st.error(
                                "⚠️ Gemini API quota has been "
                                "exceeded. Please wait and try again."
                            )

                        else:

                            st.error(
                                f"❌ Voice processing failed: "
                                f"{error_message}"
                            )


        # =================================================
        # SHOW RESULT
        # =================================================

        else:

            st.markdown(
                "### 📝 Your Transcript"
            )


            transcript_text = (
                st.session_state.voice_transcript
                or ""
            )


            st.html(
                f"""
                <div class="transcript-card">

                    {html.escape(
                        transcript_text
                    )}

                </div>
                """
            )


            st.markdown(
                "### ⭐ AI Evaluation"
            )


            score_badge(
                st.session_state.voice_score
            )


            st.write(
                dynamic_message(
                    st.session_state.voice_score
                )
            )


            ai_feedback_card(
                st.session_state.voice_feedback
            )


            # =================================================
            # NEXT VOICE QUESTION
            # =================================================

            if current_index + 1 < total_questions:

                if st.button(
                    "➡️ Next Voice Question",
                    key=f"next_voice_{current_index}",
                    use_container_width=True
                ):

                    try:

                        next_difficulty = (
                            determine_next_difficulty(
                                st.session_state.voice_score,
                                st.session_state.voice_current_difficulty
                            )
                        )


                        # IMPORTANT:
                        # select_next_topic expects:
                        # 1. selected topics
                        # 2. topic -> scores dictionary

                        next_topic = select_next_topic(
                            st.session_state.voice_selected_topics,
                            st.session_state.voice_scores
                        )


                        with st.spinner(
                            "🧠 Creating your next adaptive question..."
                        ):

                            next_question = generate_question(
                                st.session_state.voice_subject,
                                next_topic,
                                next_difficulty
                            )


                        st.session_state.voice_current_index += 1

                        st.session_state.voice_current_topic = (
                            next_topic
                        )

                        st.session_state.voice_current_difficulty = (
                            next_difficulty
                        )

                        st.session_state.voice_question = (
                            next_question
                        )

                        st.session_state.voice_answered = False

                        st.session_state.voice_feedback = None

                        st.session_state.voice_score = None

                        st.session_state.voice_transcript = None

                        st.session_state.voice_audio = None

                        st.rerun()


                    except Exception as e:

                        st.error(
                            f"❌ Could not generate next question: "
                            f"{e}"
                        )


            # =================================================
            # FINAL REPORT
            # =================================================

            else:

                st.success(
                    "🎉 Voice interview completed!"
                )

                st.markdown(
                    "## 📊 Voice Interview Report"
                )


                scores = flatten_topic_scores(
                    st.session_state.voice_scores
                )


                if scores:

                    average = (
                        sum(scores) / len(scores)
                    )


                    st.metric(
                        "Average Score",
                        f"{average:.1f}/10"
                    )


                    if average >= 8:

                        st.success(
                            "🔥 Excellent performance!"
                        )

                    elif average >= 6:

                        st.info(
                            "👍 Good performance. "
                            "Keep practicing."
                        )

                    else:

                        st.warning(
                            "💪 Keep practicing your "
                            "technical concepts."
                        )


                    st.markdown(
                        "### Question-wise Scores"
                    )


                    for i, score in enumerate(
                        scores,
                        start=1
                    ):

                        st.write(
                            f"Question {i} → ⭐ {score}/10"
                        )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title(
        "🤖 AI Interviewer"
    )

    st.markdown("---")

    st.markdown(
        """
        ### Interview Modes

        🎯 **Topic-Based**

        Practice technical subjects.

        📄 **Resume + Job**

        Get personalized questions.

        🎙️ **Voice Interview**

        Answer questions using your voice.

        ---

        ### 🧠 Adaptive AI

        The interviewer automatically changes
        question difficulty based on your
        previous performance.

        ---

        ### 📊 AI Evaluation

        Every answer receives:

        • Score  
        • Feedback  
        • Improvement suggestions
        """
    )