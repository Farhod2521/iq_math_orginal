import random
import string

from django.db import models
from django.utils import timezone

from django_app.app_user.models import Student, Class, Subject
from django_app.app_teacher.models import Question


def compute_subjects_key(subject_ids):
    """Canonical, order-independent key for a set of Subject ids, used to
    match two rooms created with the exact same subject selection."""
    return ','.join(str(i) for i in sorted(int(i) for i in subject_ids))


def generate_room_code():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(alphabet, k=6))
        if not BattleRoom.objects.filter(code=code).exists():
            return code


# Faceit's own level bands are the model here: 10 skill levels mapped to
# fixed ELO breakpoints, assigned only once a student clears placement.
LEVEL_BREAKPOINTS = [
    (1, 0, 500),
    (2, 501, 750),
    (3, 751, 900),
    (4, 901, 1050),
    (5, 1051, 1200),
    (6, 1201, 1350),
    (7, 1351, 1530),
    (8, 1531, 1750),
    (9, 1751, 2000),
    (10, 2001, None),
]


def level_for_elo(elo):
    for level, low, high in LEVEL_BREAKPOINTS:
        if high is None or elo <= high:
            if elo >= low:
                return level
    return 1


def level_progress(elo):
    """(floor, ceiling, elo_into_band, band_width, pct_to_next) for the
    level-progress widget — ceiling/pct_to_next are None at the top level."""
    level = level_for_elo(elo)
    floor, ceiling = 0, None
    for lvl, low, high in LEVEL_BREAKPOINTS:
        if lvl == level:
            floor, ceiling = low, high
            break
    if ceiling is None:
        return {'floor': floor, 'ceiling': None, 'elo_into_band': elo - floor, 'band_width': None, 'pct_to_next': None}
    band_width = ceiling - floor + 1
    elo_into_band = max(0, elo - floor)
    pct = min(100, round((elo_into_band / band_width) * 100))
    return {'floor': floor, 'ceiling': ceiling, 'elo_into_band': elo_into_band, 'band_width': band_width, 'pct_to_next': pct}


class BattleRating(models.Model):
    PLACEMENT_MATCHES = 10
    STARTING_ELO = 800  # internal-only placeholder while in placement; never shown to the player

    # Placement reveal formula: purely win/loss-driven so the outcome is
    # legible ("lose all 10 -> Level 1, ~400 ELO" per product spec), with a
    # small nudge from average per-match performance (accuracy+speed) that
    # cannot push the result past the floor/ceiling.
    PLACEMENT_BASE_ELO = 1200
    PLACEMENT_ELO_PER_MATCH = 80
    PLACEMENT_MIN_ELO = 400
    PLACEMENT_MAX_ELO = 2100

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='battle_rating')
    elo = models.PositiveIntegerField(default=0)  # 0 while in placement — frontend must never render this as a real ELO
    level = models.PositiveSmallIntegerField(default=0, verbose_name="Daraja (0 = Aniqlanmoqda)")
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    win_streak = models.PositiveIntegerField(default=0)
    best_elo = models.PositiveIntegerField(default=0)
    placement_performance_sum = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Battle reytingi"
        verbose_name_plural = "Battle reytinglari"
        ordering = ['-elo']

    def __str__(self):
        if self.is_in_placement:
            return f"{self.student.full_name} - aniqlanmoqda ({self.matches_played}/{self.PLACEMENT_MATCHES})"
        return f"{self.student.full_name} - {self.elo} ELO (L{self.level})"

    @property
    def is_in_placement(self):
        return self.matches_played < self.PLACEMENT_MATCHES

    def k_factor(self):
        if self.matches_played < 30:
            return 30
        return 20

    def record_placement_match(self, result, performance):
        """Placement matches (the student's first 10) never move a visible
        ELO number — only win/loss/draw and a performance accumulator are
        tracked. The moment the 10th match completes, a single ELO value is
        revealed via `_reveal_placement_elo`."""
        self.matches_played += 1
        if result == 'win':
            self.wins += 1
            self.win_streak += 1
        elif result == 'loss':
            self.losses += 1
            self.win_streak = 0
        else:
            self.draws += 1
            self.win_streak = 0
        self.placement_performance_sum += performance

        just_completed_placement = self.matches_played >= self.PLACEMENT_MATCHES
        if just_completed_placement:
            self._reveal_placement_elo()

        self.save(update_fields=[
            'matches_played', 'wins', 'losses', 'draws', 'win_streak',
            'placement_performance_sum', 'elo', 'best_elo', 'level', 'updated_at',
        ])
        return just_completed_placement

    def _reveal_placement_elo(self):
        net_wins = self.wins - self.losses
        avg_performance = self.placement_performance_sum / max(self.matches_played, 1)
        raw = (
            self.PLACEMENT_BASE_ELO
            + net_wins * self.PLACEMENT_ELO_PER_MATCH
            + (avg_performance - 0.5) * 100
        )
        self.elo = int(max(self.PLACEMENT_MIN_ELO, min(self.PLACEMENT_MAX_ELO, raw)))
        self.best_elo = self.elo
        self.level = level_for_elo(self.elo)

    def apply_result(self, elo_after, result):
        """Post-placement matches only — normal incremental ELO."""
        self.elo = elo_after
        self.best_elo = max(self.best_elo, elo_after)
        self.matches_played += 1
        if result == 'win':
            self.wins += 1
            self.win_streak += 1
        elif result == 'loss':
            self.losses += 1
            self.win_streak = 0
        else:
            self.draws += 1
            self.win_streak = 0
        self.level = level_for_elo(self.elo)
        self.save(update_fields=[
            'elo', 'best_elo', 'matches_played', 'wins', 'losses',
            'draws', 'win_streak', 'level', 'updated_at',
        ])


class BattleBotIdentity(models.Model):
    """A disguise: a name + avatar a bot wears in a match. Never exposed as a bot to clients."""
    name = models.CharField(max_length=100, unique=True)
    avatar_seed = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bot shaxsi"
        verbose_name_plural = "Bot shaxslari"

    def __str__(self):
        return self.name


class BattleBotDifficulty(models.Model):
    TIER_EASY = 'easy'
    TIER_MEDIUM = 'medium'
    TIER_HARD = 'hard'
    TIER_EXPERT = 'expert'
    TIER_CHOICES = [
        (TIER_EASY, 'Oson'),
        (TIER_MEDIUM, "O'rta"),
        (TIER_HARD, 'Qiyin'),
        (TIER_EXPERT, 'Ekspert'),
    ]

    tier = models.CharField(max_length=10, choices=TIER_CHOICES, unique=True)
    accuracy = models.FloatField(help_text="To'g'ri javob berish ehtimoli (0-1)")
    min_answer_seconds = models.FloatField(default=4)
    max_answer_seconds = models.FloatField(default=25)

    class Meta:
        verbose_name = "Bot qiyinchilik darajasi"
        verbose_name_plural = "Bot qiyinchilik darajalari"

    def __str__(self):
        return f"{self.get_tier_display()} ({self.accuracy * 100:.0f}%)"

    def random_answer_delay(self):
        return random.uniform(self.min_answer_seconds, self.max_answer_seconds)

    def roll_correct(self):
        return random.random() < self.accuracy


# Placement matches ramp bot difficulty deterministically: 1-3 easy, 4-6
# medium, 7-9 hard, 10 expert (see BattleRating.PLACEMENT_MATCHES).
PLACEMENT_TIER_RAMP = {
    1: BattleBotDifficulty.TIER_EASY, 2: BattleBotDifficulty.TIER_EASY, 3: BattleBotDifficulty.TIER_EASY,
    4: BattleBotDifficulty.TIER_MEDIUM, 5: BattleBotDifficulty.TIER_MEDIUM, 6: BattleBotDifficulty.TIER_MEDIUM,
    7: BattleBotDifficulty.TIER_HARD, 8: BattleBotDifficulty.TIER_HARD, 9: BattleBotDifficulty.TIER_HARD,
    10: BattleBotDifficulty.TIER_EXPERT,
}


class BattleRoom(models.Model):
    STATUS_WAITING = 'waiting'
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_WAITING, 'Kutilmoqda'),
        (STATUS_ACTIVE, 'Faol'),
        (STATUS_FINISHED, 'Yakunlandi'),
        (STATUS_CANCELLED, 'Bekor qilindi'),
    ]

    code = models.CharField(max_length=8, unique=True, default=generate_room_code)
    grade = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='battle_rooms')
    subjects = models.ManyToManyField(Subject, related_name='battle_rooms')
    subjects_key = models.CharField(
        max_length=200, db_index=True, default='',
        help_text="Sorted comma-joined subject ids — matchmaking bucket key.",
    )

    question_count = models.PositiveSmallIntegerField(default=10)
    seconds_per_question = models.PositiveSmallIntegerField(default=60)

    is_random = models.BooleanField(default=True, verbose_name="Tasodifiy raqiblar")
    chat_enabled = models.BooleanField(default=True, verbose_name="Chat yoqilgan")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_WAITING)
    current_question_index = models.PositiveSmallIntegerField(default=0)
    current_question_started_at = models.DateTimeField(null=True, blank=True)

    winner_participant = models.ForeignKey(
        'BattleParticipant', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Battle xonasi"
        verbose_name_plural = "Battle xonalari"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=[
                'status', 'is_random', 'grade', 'subjects_key',
                'question_count', 'seconds_per_question',
            ], name='battleroom_matchmaking_idx'),
        ]

    def __str__(self):
        return f"Battle #{self.id} ({self.code}) - {self.status}"

    @property
    def is_full(self):
        return self.participants.count() >= 2


class BattleParticipant(models.Model):
    room = models.ForeignKey(BattleRoom, on_delete=models.CASCADE, related_name='participants')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True, related_name='battle_participations')
    bot_identity = models.ForeignKey(BattleBotIdentity, on_delete=models.SET_NULL, null=True, blank=True)
    bot_difficulty = models.ForeignKey(BattleBotDifficulty, on_delete=models.SET_NULL, null=True, blank=True)

    is_creator = models.BooleanField(default=False)
    elo_before = models.PositiveIntegerField(default=0)
    elo_after = models.PositiveIntegerField(null=True, blank=True)

    score = models.PositiveSmallIntegerField(default=0)
    total_answer_time = models.FloatField(default=0)

    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Battle ishtirokchisi"
        verbose_name_plural = "Battle ishtirokchilari"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(student__isnull=False, bot_identity__isnull=True) |
                    models.Q(student__isnull=True, bot_identity__isnull=False)
                ),
                name='battleparticipant_exactly_one_of_student_or_bot',
            )
        ]

    def __str__(self):
        return self.display_name

    @property
    def is_bot(self):
        return self.bot_identity_id is not None

    @property
    def display_name(self):
        if self.is_bot:
            return self.bot_identity.name
        return self.student.full_name


class BattleRoomQuestion(models.Model):
    room = models.ForeignKey(BattleRoom, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='+')
    order = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Battle savoli"
        verbose_name_plural = "Battle savollari"
        unique_together = ('room', 'order')
        ordering = ['order']

    def __str__(self):
        return f"{self.room_id} - Q{self.order}"


class BattleAnswer(models.Model):
    room_question = models.ForeignKey(BattleRoomQuestion, on_delete=models.CASCADE, related_name='answers')
    participant = models.ForeignKey(BattleParticipant, on_delete=models.CASCADE, related_name='answers')

    raw_answer = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answer_time_seconds = models.FloatField(default=0)
    skipped = models.BooleanField(default=False)

    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Battle javobi"
        verbose_name_plural = "Battle javoblari"
        unique_together = ('room_question', 'participant')

    def __str__(self):
        return f"{self.participant} - Q{self.room_question.order} - {'correct' if self.is_correct else 'wrong'}"


class BattleEloLog(models.Model):
    RESULT_CHOICES = [('win', "G'alaba"), ('loss', 'Mag`lubiyat'), ('draw', 'Durrang')]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='battle_elo_logs')
    room = models.ForeignKey(BattleRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='elo_logs')

    elo_before = models.PositiveIntegerField()
    elo_after = models.PositiveIntegerField()
    elo_change = models.IntegerField()
    result = models.CharField(max_length=4, choices=RESULT_CHOICES)
    # True for every one of the student's first PLACEMENT_MATCHES rows.
    # elo_before/elo_after/elo_change stay 0 for placement rows except the
    # one where placement completes (matches_played reaches 10), which
    # carries the freshly revealed elo_after — frontend distinguishes a
    # "placement reveal" row from a "still calibrating" row by elo_after > 0.
    is_placement = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Battle ELO tarixi"
        verbose_name_plural = "Battle ELO tarixi"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at'], name='battleelolog_student_time_idx'),
        ]

    def __str__(self):
        return f"{self.student.full_name} {self.elo_before}->{self.elo_after} ({self.result})"
