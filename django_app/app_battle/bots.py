"""Bot identity/difficulty selection — kept separate from engine.py so the
"which disguise / which strength" decision has no dependency on the match
engine itself (avoids a circular import between the two)."""

import random

from .models import BattleBotIdentity, BattleBotDifficulty, BattleParticipant, BattleRoom, PLACEMENT_TIER_RAMP

RECENT_ROOMS_TO_AVOID = 5


def pick_bot_identity(student):
    recent_room_ids = list(
        BattleParticipant.objects.filter(student=student)
        .exclude(room__status=BattleRoom.STATUS_WAITING)
        .order_by('-joined_at')
        .values_list('room_id', flat=True)[:RECENT_ROOMS_TO_AVOID]
    )
    recent_bot_ids = set(
        BattleParticipant.objects.filter(room_id__in=recent_room_ids, bot_identity__isnull=False)
        .values_list('bot_identity_id', flat=True)
    )
    pool = list(BattleBotIdentity.objects.filter(is_active=True).exclude(id__in=recent_bot_ids))
    if not pool:
        pool = list(BattleBotIdentity.objects.filter(is_active=True))
    return random.choice(pool) if pool else None


# Post-placement tier weighting: nudges the bot's apparent strength toward
# the student's current ELO band without ever pinning it exactly, so bots
# feel like fair but not perfectly predictable opponents.
_ELO_BAND_WEIGHTS = [
    (900, {'easy': 0.50, 'medium': 0.35, 'hard': 0.12, 'expert': 0.03}),
    (1300, {'easy': 0.20, 'medium': 0.45, 'hard': 0.28, 'expert': 0.07}),
    (1700, {'easy': 0.05, 'medium': 0.25, 'hard': 0.45, 'expert': 0.25}),
    (None, {'easy': 0.02, 'medium': 0.13, 'hard': 0.35, 'expert': 0.50}),
]


def pick_bot_difficulty(rating):
    if rating.is_in_placement:
        match_number = rating.matches_played + 1
        tier = PLACEMENT_TIER_RAMP.get(match_number, BattleBotDifficulty.TIER_EASY)
        return BattleBotDifficulty.objects.filter(tier=tier).first()

    weights = _ELO_BAND_WEIGHTS[-1][1]
    for ceiling, band_weights in _ELO_BAND_WEIGHTS:
        if ceiling is None or rating.elo < ceiling:
            weights = band_weights
            break

    tiers = list(weights.keys())
    probs = list(weights.values())
    chosen_tier = random.choices(tiers, weights=probs, k=1)[0]
    return BattleBotDifficulty.objects.filter(tier=chosen_tier).first()


def bot_elo_before(student_elo):
    return max(0, min(3000, student_elo + random.randint(-80, 40)))
