"""Faceit-style ELO with a performance multiplier.

Pure functions only (no DB access) so the whole formula is unit-testable in
isolation from matchmaking/consumer plumbing.
"""

MIN_DELTA = 8
MAX_DELTA = 40
ZERO_THRESHOLD = 1.0

ACCURACY_WEIGHT = 0.7
SPEED_WEIGHT = 0.3
PERFORMANCE_MULTIPLIER_MIN = 0.6
PERFORMANCE_MULTIPLIER_MAX = 1.6

_ACTUAL_SCORE = {'win': 1.0, 'draw': 0.5, 'loss': 0.0}


def expected_score(elo_self, elo_opponent):
    return 1 / (1 + 10 ** ((elo_opponent - elo_self) / 400))


def performance_score(correct_count, question_count, avg_seconds_on_correct, seconds_per_question):
    """Blends accuracy (0.7) and speed-on-correct-answers only (0.3), so
    fast wrong guesses are never rewarded."""
    if question_count <= 0:
        return 0.0
    accuracy = correct_count / question_count
    if avg_seconds_on_correct is None or seconds_per_question <= 0:
        speed = 0.0
    else:
        speed = max(0.0, 1 - (avg_seconds_on_correct / seconds_per_question))
    return accuracy * ACCURACY_WEIGHT + speed * SPEED_WEIGHT


def match_outcome(score_a, time_a, score_b, time_b):
    """More correct answers wins; ties broken by lower total answer time;
    still tied = draw. Returns (result_a, result_b)."""
    if score_a > score_b:
        return 'win', 'loss'
    if score_b > score_a:
        return 'loss', 'win'
    if time_a < time_b:
        return 'win', 'loss'
    if time_b < time_a:
        return 'loss', 'win'
    return 'draw', 'draw'


def compute_elo_delta(elo_self, elo_opponent, result, k, performance):
    """`result` is 'win'/'loss'/'draw' from self's perspective.

    A true coin-flip draw (elo_self == elo_opponent) yields 0. Otherwise the
    magnitude is clamped to [MIN_DELTA, MAX_DELTA] with the sign always taken
    from the unclamped raw delta, so a winner can never lose ELO and a loser
    can never gain ELO regardless of the performance multiplier.
    """
    actual = _ACTUAL_SCORE[result]
    expected = expected_score(elo_self, elo_opponent)
    raw_delta = k * (actual - expected)

    if abs(raw_delta) < ZERO_THRESHOLD:
        return 0

    multiplier = min(max(PERFORMANCE_MULTIPLIER_MIN + performance, PERFORMANCE_MULTIPLIER_MIN), PERFORMANCE_MULTIPLIER_MAX)
    sign = 1 if raw_delta > 0 else -1
    clamped_abs = min(max(abs(raw_delta * multiplier), MIN_DELTA), MAX_DELTA)
    return int(round(sign * clamped_abs))
