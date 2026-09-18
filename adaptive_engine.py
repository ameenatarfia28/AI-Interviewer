from collections import defaultdict


DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]



def determine_next_difficulty(score, current_difficulty):
    """Adapt difficulty using the previous answer score."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return current_difficulty

    current = str(current_difficulty).title()

    if current not in DIFFICULTY_ORDER:
        current = "Medium"

    index = DIFFICULTY_ORDER.index(current)

    if score >= 8:
        index = min(index + 1, len(DIFFICULTY_ORDER) - 1)
    elif score <= 4:
        index = max(index - 1, 0)

    return DIFFICULTY_ORDER[index]



def select_next_topic(selected_topics, topic_scores):
    """
    Choose a topic using topic-level performance.

    topic_scores format:
        {
            "OOP": [8, 7],
            "Inheritance": [5]
        }
    """
    if not selected_topics:
        raise ValueError("No interview topics were selected.")

    scores = topic_scores or {}

    # Prefer topics that have not been answered yet.
    unused = [topic for topic in selected_topics if topic not in scores]
    if unused:
        return unused[0]

    # Otherwise choose the weakest average topic.
    def average(topic):
        values = scores.get(topic, [])
        if not values:
            return 0.0
        numeric = []
        for value in values:
            try:
                numeric.append(float(value))
            except (TypeError, ValueError):
                pass
        return sum(numeric) / len(numeric) if numeric else 0.0

    return min(selected_topics, key=average)



def select_next_question(question_pool, target_difficulty, used_questions):
    """Pick an unused question close to the adaptive difficulty."""
    used_questions = set(used_questions or [])

    available = [
        item for item in question_pool
        if item.get("question") not in used_questions
    ]

    if not available:
        return None

    target = str(target_difficulty).title()

    # Exact difficulty first.
    for item in available:
        if str(item.get("difficulty", "Medium")).title() == target:
            return item

    # Fall back to nearest difficulty.
    try:
        target_idx = DIFFICULTY_ORDER.index(target)
    except ValueError:
        target_idx = 1

    return min(
        available,
        key=lambda item: abs(
            DIFFICULTY_ORDER.index(
                str(item.get("difficulty", "Medium")).title()
                if str(item.get("difficulty", "Medium")).title() in DIFFICULTY_ORDER
                else "Medium"
            ) - target_idx
        )
    )