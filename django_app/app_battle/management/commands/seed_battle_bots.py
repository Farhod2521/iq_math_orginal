from django.core.management.base import BaseCommand

from django_app.app_battle.models import BattleBotIdentity, BattleBotDifficulty

BOT_NAMES = [
    "Sardor Aliyev", "Malika Yusupova", "Javohir Rashidov", "Dilnoza Karimova",
    "Otabek Nazarov", "Nilufar Tosheva", "Bekzod Ergashev", "Gulnora Saidova",
    "Sherzod Umarov", "Zarina Abdullayeva", "Farrux Xoliqov", "Madina Yoldasheva",
    "Jasur Mirzayev", "Sevinch Qodirova", "Aziz Turgunov",
]

DIFFICULTY_TIERS = [
    {"tier": BattleBotDifficulty.TIER_EASY, "accuracy": 0.50, "min_answer_seconds": 12, "max_answer_seconds": 45},
    {"tier": BattleBotDifficulty.TIER_MEDIUM, "accuracy": 0.68, "min_answer_seconds": 8, "max_answer_seconds": 30},
    {"tier": BattleBotDifficulty.TIER_HARD, "accuracy": 0.82, "min_answer_seconds": 5, "max_answer_seconds": 20},
    {"tier": BattleBotDifficulty.TIER_EXPERT, "accuracy": 0.93, "min_answer_seconds": 3, "max_answer_seconds": 14},
]


class Command(BaseCommand):
    help = "Seeds the fixed pool of Battle bot identities and difficulty tiers (idempotent)."

    def handle(self, *args, **options):
        created_identities = 0
        for name in BOT_NAMES:
            _, created = BattleBotIdentity.objects.get_or_create(
                name=name, defaults={"avatar_seed": name.lower().replace(" ", "_")},
            )
            created_identities += int(created)

        created_tiers = 0
        for tier in DIFFICULTY_TIERS:
            _, created = BattleBotDifficulty.objects.update_or_create(
                tier=tier["tier"], defaults={
                    "accuracy": tier["accuracy"],
                    "min_answer_seconds": tier["min_answer_seconds"],
                    "max_answer_seconds": tier["max_answer_seconds"],
                },
            )
            created_tiers += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Battle bots seeded: {created_identities} new identities, "
            f"{created_tiers} new difficulty tiers (existing tiers updated)."
        ))
