from django.contrib import admin

from .models import (
    BattleRating, BattleBotIdentity, BattleBotDifficulty, BattleRoom,
    BattleParticipant, BattleRoomQuestion, BattleAnswer, BattleEloLog,
)


@admin.register(BattleRating)
class BattleRatingAdmin(admin.ModelAdmin):
    list_display = ('student', 'elo', 'level', 'matches_played', 'wins', 'losses', 'draws', 'win_streak')
    search_fields = ('student__full_name',)
    list_filter = ('level',)


@admin.register(BattleBotIdentity)
class BattleBotIdentityAdmin(admin.ModelAdmin):
    list_display = ('name', 'avatar_seed', 'is_active')
    list_filter = ('is_active',)


@admin.register(BattleBotDifficulty)
class BattleBotDifficultyAdmin(admin.ModelAdmin):
    list_display = ('tier', 'accuracy', 'min_answer_seconds', 'max_answer_seconds')


class BattleParticipantInline(admin.TabularInline):
    model = BattleParticipant
    extra = 0


@admin.register(BattleRoom)
class BattleRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'grade', 'difficulty_level', 'status', 'is_random', 'created_at')
    list_filter = ('status', 'is_random', 'grade', 'difficulty_level')
    search_fields = ('code',)
    filter_horizontal = ('subjects',)
    inlines = [BattleParticipantInline]


@admin.register(BattleEloLog)
class BattleEloLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'elo_before', 'elo_after', 'elo_change', 'result', 'created_at')
    list_filter = ('result',)
    search_fields = ('student__full_name',)


admin.site.register(BattleParticipant)
admin.site.register(BattleRoomQuestion)
admin.site.register(BattleAnswer)
