import html

import streamlit as st

from adaptive_engine import (
    determine_next_difficulty,
    select_next_question,
    select_next_topic,
)
from config import is_quota_error, is_service_unavailable_error
from llm import (
    evaluate_answer,
    format_evaluation,
    generate_question_pool,
)
from resume_analyzer import analyze_resume_job
from resume_parser import extract_resume_text
from topics import SUBJECT_TOPICS
from voice_engine import analyze_voice_answer


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Interviewer",
    page_icon="🤖",
    layout="wide",
)


# =========================================================
# PREMIUM UI
# =========================================================

st.markdown(
    """
    <style>
    .stApp { background: #080b12; color: #f5f7fb; }
    .main { padding: 2rem; }
    .hero { text-align: center; padding: 30px 10px; }
    .hero-title { font-size: 48px; font-weight: 800; color: #fff; }
    .hero-subtitle { font-size: 18px; color: #9ca3af; margin-bottom: 25px; }
    .feature-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px; min-height: 150px; }
    .feature-title { font-size: 20px; font-weight: 700; margin-bottom: 10px; }
    .feature-text { color: #9ca3af; line-height: 1.6; }
    .question-card { background: #111827; border: 1px solid #263244; border-radius: 18px; padding: 28px; margin-top: 20px; margin-bottom: 20px; }
    .question-label { color: #60a5fa; font-weight: 700; font-size: 14px; margin-bottom: 10px; }
    .question-text { font-size: 22px; font-weight: 600; line-height: 1.5; color: #fff; }
    .feedback-card { background: #101827; border-left: 4px solid #60a5fa; border-radius: 12px; padding: 20px; margin-top: 15px; }
    .score-badge { background: #172554; color: #93c5fd; padding: 10px 18px; border-radius: 20px; font-size: 18px; font-weight: 700; display: inline-block; margin: 10px 0; }
    .transcript-card { background: #111827; border: 1px solid #374151; border-radius: 12px; padding: 20px; margin-top: 15px; line-height: 1.7; }
    .speed-note { padding: 12px 16px; border-radius: 10px; background: #0f172a; border: 1px solid #1e293b; color: #cbd5e1; margin: 10px 0 20px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "topic_started": False,
    "topic_pool": [],
    "topic_used_questions": [],
    "topic_current_index": 0,
    "topic_question": None,
    "topic_current_topic": None,
    "topic_current_difficulty": "Medium",
    "topic_answered": False,
    "topic_score": None,
    "topic_feedback": None,
    "topic_scores": {},
    "topic_history": [],
    "topic_subject": None,
    "topic_selected_topics": [],
    "topic_total_questions": 5,

    "resume_started": False,
    "resume_pool": [],
    "resume_used_questions": [],
    "resume_current_index": 0,
    "resume_question": None,
    "resume_current_topic": None,
    "resume_current_difficulty": "Medium",
    "resume_answered": False,
    "resume_score": None,
    "resume_feedback": None,
    "resume_scores": [],
    "resume_history": [],
    "resume_total_questions": 5,
    "resume_analysis": None,
    "job_analysis": None,
    "match_analysis": None,
    "matched_skills": [],
    "missing_skills": [],

    "voice_started": False,
    "voice_pool": [],
    "voice_used_questions": [],
    "voice_current_index": 0,
    "voice_question": None,
    "voice_current_topic": None,
    "voice_current_difficulty": "Medium",
    "voice_answered": False,
    "voice_score": None,
    "voice_feedback": None,
    "voice_transcript": None,
    "voice_scores": {},
    "voice_history": [],
    "voice_subject": None,
    "voice_selected_topics": [],
    "voice_total_questions": 5,
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPERS
# =========================================================

def question_card(question, number, difficulty, topic):
    st.html(
        f"""
        <div class='question-card'>
            <div class='question-label'>
                QUESTION {number} • {html.escape(str(difficulty))} • {html.escape(str(topic))}
            </div>
            <div class='question-text'>
                {html.escape(str(question))}
            </div>
        </div>
        """
    )



def score_badge(score):
    st.html(
        f"<div class='score-badge'>⭐ Score: {score}/10</div>"
    )



def dynamic_message(score):
    score = float(score or 0)
    if score >= 9:
        return "🔥 Excellent answer!"
    if score >= 7:
        return "👏 Good answer!"
    if score >= 5:
        return "👍 Decent answer. Add more technical depth."
    return "💡 Keep practicing the core concepts."



def feedback_card(markdown_text):
    safe = html.escape(str(markdown_text)).replace("\n", "<br>")
    st.html(f"<div class='feedback-card'>{safe}</div>")



def handle_ai_error(error):
    if is_quota_error(error):
        st.error(
            "⚠️ Gemini quota/rate limit reached. "
            "Please wait for the quota window to reset before retrying."
        )
    elif is_service_unavailable_error(error):
        st.warning(
            "⚡ Gemini is temporarily busy. The app tried the fast model "
            "and its fallback. Please wait a few seconds and retry."
        )
    else:
        st.error(f"❌ AI request failed: {error}")



def next_from_pool(pool, difficulty, used_questions):
    item = select_next_question(pool, difficulty, used_questions)
    if item is None:
        return None
    return item


# =========================================================
# HERO
# =========================================================

st.html(
    """
    <div class='hero'>
        <div class='hero-title'>🤖 AI Interviewer</div>
        <div class='hero-subtitle'>Practice smarter. Get evaluated. Improve continuously.</div>
    </div>
    """
)


col1, col2, col3 = st.columns(3)

with col1:
    st.html(
        """
        <div class='feature-card'>
            <div class='feature-title'>🎯 Topic-Based</div>
            <div class='feature-text'>Practice Python, Java, SQL, Machine Learning, DSA and other technical subjects.</div>
        </div>
        """
    )

with col2:
    st.html(
        """
        <div class='feature-card'>
            <div class='feature-title'>📄 Resume-Aware</div>
            <div class='feature-text'>Analyze your resume against a job description and get personalized questions.</div>
        </div>
        """
    )

with col3:
    st.html(
        """
        <div class='feature-card'>
            <div class='feature-title'>🎙️ Voice Interview</div>
            <div class='feature-text'>Answer using your microphone and receive transcript, score and feedback in one AI call.</div>
        </div>
        """
    )

st.write("")

st.markdown("### Choose Interview Mode")

selected_mode = st.segmented_control(
    "Interview Mode",
    options=[
        "🎯 Topic-Based Interview",
        "📄 Resume + Job Interview",
        "🎙️ Voice Interview",
    ],
    selection_mode="single",
    default="🎯 Topic-Based Interview",
    required=True,
    key="interview_mode",
    width="stretch",
    label_visibility="collapsed",
)


# =========================================================
# TOPIC MODE
# =========================================================

if selected_mode == "🎯 Topic-Based Interview":
    st.subheader("🎯 Topic-Based Interview")

    if not st.session_state.topic_started:
        c1, c2 = st.columns(2)

        with c1:
            subject = st.selectbox(
                "Choose Subject",
                list(SUBJECT_TOPICS.keys()),
                key="topic_subject_select",
            )
            difficulty = st.selectbox(
                "Starting Difficulty",
                ["Easy", "Medium", "Hard"],
                index=1,
                key="topic_difficulty_select",
            )

        with c2:
            available_topics = SUBJECT_TOPICS[subject]
            selected_topics = st.multiselect(
                "Select Topics",
                available_topics,
                default=available_topics[:3],
                key="topic_selected_topics_select",
            )
            total_questions = st.number_input(
                "Number of Questions",
                min_value=1,
                max_value=20,
                value=5,
                key="topic_total_questions_input",
            )

        st.markdown(
            "<div class='speed-note'>⚡ Questions are generated as a reusable pool once. Next Question is selected locally, so there is no Gemini wait for every question.</div>",
            unsafe_allow_html=True,
        )

        if st.button("🚀 Start Interview", key="start_topic", use_container_width=True):
            if not selected_topics:
                st.warning("Please select at least one topic.")
            else:
                try:
                    with st.spinner("⚡ Preparing your question pool..."):
                        pool = generate_question_pool(
                            subject,
                            tuple(selected_topics),
                            int(total_questions),
                            difficulty,
                        )

                    first = next_from_pool(pool, difficulty, [])
                    if first is None:
                        raise RuntimeError("No question was available.")

                    st.session_state.topic_started = True
                    st.session_state.topic_pool = pool
                    st.session_state.topic_used_questions = [first["question"]]
                    st.session_state.topic_current_index = 0
                    st.session_state.topic_question = first["question"]
                    st.session_state.topic_current_topic = first["topic"]
                    st.session_state.topic_current_difficulty = first["difficulty"]
                    st.session_state.topic_subject = subject
                    st.session_state.topic_selected_topics = list(selected_topics)
                    st.session_state.topic_total_questions = int(total_questions)
                    st.session_state.topic_answered = False
                    st.session_state.topic_score = None
                    st.session_state.topic_feedback = None
                    st.session_state.topic_scores = {}
                    st.session_state.topic_history = []
                    st.rerun()
                except Exception as error:
                    handle_ai_error(error)

    if st.session_state.topic_started:
        idx = st.session_state.topic_current_index
        total = st.session_state.topic_total_questions

        question_card(
            st.session_state.topic_question,
            idx + 1,
            st.session_state.topic_current_difficulty,
            st.session_state.topic_current_topic,
        )

        if not st.session_state.topic_answered:
            answer = st.text_area(
                "Your Answer",
                height=180,
                key=f"topic_answer_{idx}",
            )

            if st.button("🤖 Evaluate Answer", key=f"topic_eval_{idx}", use_container_width=True):
                if not answer.strip():
                    st.warning("Please enter your answer.")
                else:
                    try:
                        with st.spinner("🤖 Evaluating your answer..."):
                            evaluation = evaluate_answer(
                                st.session_state.topic_question,
                                answer,
                                st.session_state.topic_subject,
                            )

                        score = evaluation["score"]
                        topic = st.session_state.topic_current_topic

                        st.session_state.topic_score = score
                        st.session_state.topic_feedback = format_evaluation(evaluation)
                        st.session_state.topic_answered = True

                        st.session_state.topic_scores.setdefault(topic, []).append(score)
                        st.session_state.topic_history.append({
                            "question": st.session_state.topic_question,
                            "topic": topic,
                            "difficulty": st.session_state.topic_current_difficulty,
                            "answer": answer,
                            "score": score,
                            "feedback": evaluation,
                        })
                        st.rerun()
                    except Exception as error:
                        handle_ai_error(error)
        else:
            score_badge(st.session_state.topic_score)
            st.write(dynamic_message(st.session_state.topic_score))
            feedback_card(st.session_state.topic_feedback)

            if idx + 1 < total:
                if st.button("➡️ Next Question", key=f"topic_next_{idx}", use_container_width=True):
                    try:
                        next_difficulty = determine_next_difficulty(
                            st.session_state.topic_score,
                            st.session_state.topic_current_difficulty,
                        )
                        next_topic = select_next_topic(
                            st.session_state.topic_selected_topics,
                            st.session_state.topic_scores,
                        )
                        item = next_from_pool(
                            st.session_state.topic_pool,
                            next_difficulty,
                            st.session_state.topic_used_questions,
                        )

                        if item is None:
                            # Use any unused question when the exact adaptive level is exhausted.
                            remaining = [
                                q for q in st.session_state.topic_pool
                                if q["question"] not in st.session_state.topic_used_questions
                            ]
                            if not remaining:
                                raise RuntimeError("Question pool exhausted.")
                            item = remaining[0]

                        # Prefer the selected topic when an unused question exists.
                        topic_matches = [
                            q for q in st.session_state.topic_pool
                            if q["question"] not in st.session_state.topic_used_questions
                            and q["topic"] == next_topic
                        ]
                        if topic_matches:
                            exact = [
                                q for q in topic_matches
                                if q["difficulty"] == next_difficulty
                            ]
                            item = (exact or topic_matches)[0]

                        st.session_state.topic_current_index += 1
                        st.session_state.topic_current_topic = item["topic"]
                        st.session_state.topic_current_difficulty = item["difficulty"]
                        st.session_state.topic_question = item["question"]
                        st.session_state.topic_used_questions.append(item["question"])
                        st.session_state.topic_answered = False
                        st.session_state.topic_score = None
                        st.session_state.topic_feedback = None
                        st.rerun()
                    except Exception as error:
                        handle_ai_error(error)
            else:
                st.success("🎉 Topic interview completed!")
                scores = [score for values in st.session_state.topic_scores.values() for score in values]
                if scores:
                    st.metric("Average Score", f"{sum(scores) / len(scores):.1f}/10")
                    for number, score in enumerate(scores, start=1):
                        st.write(f"Question {number}: ⭐ {score}/10")


# =========================================================
# RESUME + JD MODE
# =========================================================

elif selected_mode == "📄 Resume + Job Interview":
    st.subheader("📄 Resume + Job Description Interview")

    if not st.session_state.resume_started:
        resume_file = st.file_uploader(
            "Upload Resume",
            type=["pdf"],
            key="resume_upload",
        )

        job_description = st.text_area(
            "Paste Job Description",
            height=180,
            key="job_description",
        )

        total_questions = st.number_input(
            "Number of Questions",
            min_value=1,
            max_value=20,
            value=5,
            key="resume_total_questions_input",
        )

        st.markdown(
            "<div class='speed-note'>⚡ Resume extraction is local. Resume analysis, JD analysis, matching, and the question pool are produced in one Gemini request.</div>",
            unsafe_allow_html=True,
        )

        if st.button("🚀 Start Resume Interview", key="start_resume", use_container_width=True):
            if resume_file is None:
                st.warning("Please upload your resume.")
            elif not job_description.strip():
                st.warning("Please enter the job description.")
            else:
                try:
                    with st.spinner("⚡ Analyzing Resume + JD and preparing questions..."):
                        resume_text = extract_resume_text(resume_file)
                        result = analyze_resume_job(
                            resume_text,
                            job_description,
                            int(total_questions),
                        )

                    first = result["questions"][0]

                    st.session_state.resume_started = True
                    st.session_state.resume_pool = result["questions"]
                    st.session_state.resume_used_questions = [first["question"]]
                    st.session_state.resume_current_index = 0
                    st.session_state.resume_question = first["question"]
                    st.session_state.resume_current_topic = first["topic"]
                    st.session_state.resume_current_difficulty = first["difficulty"]
                    st.session_state.resume_answered = False
                    st.session_state.resume_score = None
                    st.session_state.resume_feedback = None
                    st.session_state.resume_scores = []
                    st.session_state.resume_history = []
                    st.session_state.resume_total_questions = int(total_questions)
                    st.session_state.resume_analysis = result["resume_summary"]
                    st.session_state.job_analysis = result["job_summary"]
                    st.session_state.match_analysis = result["match_summary"]
                    st.session_state.matched_skills = result["matched_skills"]
                    st.session_state.missing_skills = result["missing_skills"]
                    st.rerun()
                except Exception as error:
                    handle_ai_error(error)

    if st.session_state.resume_started:
        idx = st.session_state.resume_current_index
        total = st.session_state.resume_total_questions

        with st.expander("🔍 View Resume ↔ Job Analysis"):
            st.markdown("### 📄 Resume Analysis")
            st.write(st.session_state.resume_analysis)
            st.markdown("### 💼 Job Description Analysis")
            st.write(st.session_state.job_analysis)
            st.markdown("### 🎯 Resume–Job Match")
            st.write(st.session_state.match_analysis)
            if st.session_state.matched_skills:
                st.write("**Matched skills:**", ", ".join(st.session_state.matched_skills))
            if st.session_state.missing_skills:
                st.write("**Missing/less-evident skills:**", ", ".join(st.session_state.missing_skills))

        question_card(
            st.session_state.resume_question,
            idx + 1,
            st.session_state.resume_current_difficulty,
            st.session_state.resume_current_topic,
        )

        if not st.session_state.resume_answered:
            answer = st.text_area(
                "Your Answer",
                height=180,
                key=f"resume_answer_{idx}",
            )

            if st.button("🤖 Evaluate Answer", key=f"resume_eval_{idx}", use_container_width=True):
                if not answer.strip():
                    st.warning("Please enter your answer.")
                else:
                    try:
                        with st.spinner("🤖 Evaluating your answer..."):
                            evaluation = evaluate_answer(
                                st.session_state.resume_question,
                                answer,
                                "Resume + Job Interview",
                            )

                        st.session_state.resume_score = evaluation["score"]
                        st.session_state.resume_feedback = format_evaluation(evaluation)
                        st.session_state.resume_scores.append(evaluation["score"])
                        st.session_state.resume_history.append({
                            "question": st.session_state.resume_question,
                            "answer": answer,
                            "score": evaluation["score"],
                            "feedback": evaluation,
                        })
                        st.session_state.resume_answered = True
                        st.rerun()
                    except Exception as error:
                        handle_ai_error(error)
        else:
            score_badge(st.session_state.resume_score)
            feedback_card(st.session_state.resume_feedback)

            if idx + 1 < total:
                if st.button("➡️ Next Question", key=f"resume_next_{idx}", use_container_width=True):
                    next_difficulty = determine_next_difficulty(
                        st.session_state.resume_score,
                        st.session_state.resume_current_difficulty,
                    )
                    item = next_from_pool(
                        st.session_state.resume_pool,
                        next_difficulty,
                        st.session_state.resume_used_questions,
                    )
                    if item is None:
                        item = next(
                            q for q in st.session_state.resume_pool
                            if q["question"] not in st.session_state.resume_used_questions
                        )

                    st.session_state.resume_current_index += 1
                    st.session_state.resume_question = item["question"]
                    st.session_state.resume_current_topic = item["topic"]
                    st.session_state.resume_current_difficulty = item["difficulty"]
                    st.session_state.resume_used_questions.append(item["question"])
                    st.session_state.resume_answered = False
                    st.session_state.resume_score = None
                    st.session_state.resume_feedback = None
                    st.rerun()
            else:
                st.success("🎉 Resume interview completed!")
                if st.session_state.resume_scores:
                    average = sum(st.session_state.resume_scores) / len(st.session_state.resume_scores)
                    st.metric("Average Score", f"{average:.1f}/10")


# =========================================================
# VOICE MODE
# =========================================================

elif selected_mode == "🎙️ Voice Interview":
    st.subheader("🎙️ Voice Interview")
    st.write(
        "Answer by voice. The optimized flow uses one AI call to return "
        "speech detection, transcript, score and feedback."
    )

    if not st.session_state.voice_started:
        c1, c2 = st.columns(2)

        with c1:
            voice_subject = st.selectbox(
                "Choose Subject",
                list(SUBJECT_TOPICS.keys()),
                key="voice_subject_select",
            )
            voice_difficulty = st.selectbox(
                "Starting Difficulty",
                ["Easy", "Medium", "Hard"],
                index=1,
                key="voice_difficulty_select",
            )

        with c2:
            available_topics = SUBJECT_TOPICS[voice_subject]
            voice_topics = st.multiselect(
                "Select Topics",
                available_topics,
                default=available_topics[:3],
                key="voice_topics_select",
            )
            voice_total = st.number_input(
                "Number of Questions",
                min_value=1,
                max_value=20,
                value=5,
                key="voice_total_questions_input",
            )

        st.markdown(
            "<div class='speed-note'>⚡ Questions are prepared once. Each voice answer uses one AI request for transcript + evaluation instead of separate transcription and evaluation calls.</div>",
            unsafe_allow_html=True,
        )

        if st.button("🎙️ Start Voice Interview", key="start_voice", use_container_width=True):
            if not voice_topics:
                st.warning("Please select at least one topic.")
            else:
                try:
                    with st.spinner("⚡ Preparing voice interview question pool..."):
                        pool = generate_question_pool(
                            voice_subject,
                            tuple(voice_topics),
                            int(voice_total),
                            voice_difficulty,
                        )

                    first = next_from_pool(pool, voice_difficulty, [])
                    if first is None:
                        raise RuntimeError("No question was available.")

                    st.session_state.voice_started = True
                    st.session_state.voice_pool = pool
                    st.session_state.voice_used_questions = [first["question"]]
                    st.session_state.voice_current_index = 0
                    st.session_state.voice_question = first["question"]
                    st.session_state.voice_current_topic = first["topic"]
                    st.session_state.voice_current_difficulty = first["difficulty"]
                    st.session_state.voice_answered = False
                    st.session_state.voice_score = None
                    st.session_state.voice_feedback = None
                    st.session_state.voice_transcript = None
                    st.session_state.voice_scores = {}
                    st.session_state.voice_history = []
                    st.session_state.voice_subject = voice_subject
                    st.session_state.voice_selected_topics = list(voice_topics)
                    st.session_state.voice_total_questions = int(voice_total)
                    st.rerun()
                except Exception as error:
                    handle_ai_error(error)

    if st.session_state.voice_started:
        idx = st.session_state.voice_current_index
        total = st.session_state.voice_total_questions

        question_card(
            st.session_state.voice_question,
            idx + 1,
            st.session_state.voice_current_difficulty,
            st.session_state.voice_current_topic,
        )

        if not st.session_state.voice_answered:
            st.markdown("### 🎙️ Record Your Answer")
            audio_value = st.audio_input(
                "🎙️ Record your answer",
                key=f"voice_record_{idx}",
            )

            if audio_value is not None:
                st.audio(audio_value, format="audio/wav")
                st.success("✅ Recording captured.")

                if st.button(
                    "🤖 Analyze Voice Answer",
                    key=f"voice_analyze_{idx}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("⚡ Transcribing + evaluating in one AI call..."):
                            result = analyze_voice_answer(
                                audio_value.getvalue(),
                                audio_value.type or "audio/wav",
                                st.session_state.voice_question,
                                st.session_state.voice_subject,
                            )

                        topic = st.session_state.voice_current_topic
                        score = result["score"]

                        st.session_state.voice_transcript = result["transcript"]
                        st.session_state.voice_score = score
                        st.session_state.voice_feedback = (
                            result["feedback"]
                            + "\n\n**Strengths**\n"
                            + "\n".join(f"- {x}" for x in result["strengths"])
                            + "\n\n**Improvements**\n"
                            + "\n".join(f"- {x}" for x in result["improvements"])
                            + f"\n\n**Score: {score}/10**"
                        )
                        st.session_state.voice_scores.setdefault(topic, []).append(score)
                        st.session_state.voice_history.append(result)
                        st.session_state.voice_answered = True
                        st.rerun()
                    except ValueError as error:
                        if str(error) == "NO_SPEECH_DETECTED":
                            st.warning(
                                "🎙️ No speech was detected. Please record your answer again and speak clearly."
                            )
                        else:
                            st.error(f"❌ {error}")
                    except Exception as error:
                        handle_ai_error(error)
        else:
            st.markdown("### 📝 Transcript")
            st.html(
                f"<div class='transcript-card'>{html.escape(st.session_state.voice_transcript or '')}</div>"
            )

            st.markdown("### ⭐ AI Evaluation")
            score_badge(st.session_state.voice_score)
            st.write(dynamic_message(st.session_state.voice_score))
            feedback_card(st.session_state.voice_feedback)

            if idx + 1 < total:
                if st.button(
                    "➡️ Next Voice Question",
                    key=f"voice_next_{idx}",
                    use_container_width=True,
                ):
                    try:
                        next_difficulty = determine_next_difficulty(
                            st.session_state.voice_score,
                            st.session_state.voice_current_difficulty,
                        )
                        next_topic = select_next_topic(
                            st.session_state.voice_selected_topics,
                            st.session_state.voice_scores,
                        )
                        item = next_from_pool(
                            st.session_state.voice_pool,
                            next_difficulty,
                            st.session_state.voice_used_questions,
                        )

                        if item is None:
                            remaining = [
                                q for q in st.session_state.voice_pool
                                if q["question"] not in st.session_state.voice_used_questions
                            ]
                            if not remaining:
                                raise RuntimeError("Question pool exhausted.")
                            item = remaining[0]

                        topic_matches = [
                            q for q in st.session_state.voice_pool
                            if q["question"] not in st.session_state.voice_used_questions
                            and q["topic"] == next_topic
                        ]
                        if topic_matches:
                            exact = [
                                q for q in topic_matches
                                if q["difficulty"] == next_difficulty
                            ]
                            item = (exact or topic_matches)[0]

                        st.session_state.voice_current_index += 1
                        st.session_state.voice_question = item["question"]
                        st.session_state.voice_current_topic = item["topic"]
                        st.session_state.voice_current_difficulty = item["difficulty"]
                        st.session_state.voice_used_questions.append(item["question"])
                        st.session_state.voice_answered = False
                        st.session_state.voice_score = None
                        st.session_state.voice_feedback = None
                        st.session_state.voice_transcript = None
                        st.rerun()
                    except Exception as error:
                        handle_ai_error(error)
            else:
                st.success("🎉 Voice interview completed!")
                scores = [score for values in st.session_state.voice_scores.values() for score in values]
                if scores:
                    st.metric("Average Score", f"{sum(scores) / len(scores):.1f}/10")
                    for number, score in enumerate(scores, start=1):
                        st.write(f"Question {number}: ⭐ {score}/10")


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.title("🤖 AI Interviewer")
    st.markdown("---")
    st.markdown(
        """
        ### Interview Modes

        🎯 **Topic-Based**
        Practice technical subjects.

        📄 **Resume + Job**
        Get personalized questions from your resume and JD.

        🎙️ **Voice Interview**
        Get transcript + score + feedback from one AI request.

        ---

        ### ⚡ Speed Optimization

        • Reusable question pools
        • Fewer Gemini calls
        • Structured JSON responses
        • Streamlit caching
        • One-call voice evaluation
        """
    )
