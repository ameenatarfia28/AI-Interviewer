def determine_next_difficulty(score, current_difficulty):
    """
    Determine the difficulty of the next question
    based on the candidate's previous score.
    """

    difficulties = ["Easy", "Medium", "Hard"]

    current_index = difficulties.index(current_difficulty)

    # Excellent answer
    if score >= 8:

        if current_index < len(difficulties) - 1:
            return difficulties[current_index + 1]

        return "Hard"

    # Average answer
    elif score >= 5:

        return current_difficulty

    # Weak answer
    else:

        if current_index > 0:
            return difficulties[current_index - 1]

        return "Easy"
def select_next_topic(
    selected_topics,
    topic_scores
):
    """
    Select the next topic based on performance.
    """

    # Topics that have not been asked yet
    for topic in selected_topics:

        if topic not in topic_scores:
            return topic

    # Find topic with lowest average score
    weakest_topic = None
    weakest_average = 11

    for topic in selected_topics:

        scores = topic_scores.get(topic, [])

        if scores:

            average = sum(scores) / len(scores)

            if average < weakest_average:

                weakest_average = average
                weakest_topic = topic

    if weakest_topic:
        return weakest_topic

    return selected_topics[0]