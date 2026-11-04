from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline

from .models import LigaAttempt, LigaChoice, LigaParticipant, LigaQuestion, LigaSeason, LigaTest, LigaWinner


@admin.register(LigaSeason)
class LigaSeasonAdmin(TranslationAdmin):
    list_display = ('number', 'weeks_count', 'is_published', 'closed_at')
    list_filter = ('is_published',)
    readonly_fields = ('closed_at',)


@admin.register(LigaTest)
class LigaTestAdmin(admin.ModelAdmin):
    list_display = ('season', 'week_number', 'grade', 'start_at', 'end_at', 'duration_minutes', 'question_count', 'is_published')
    list_filter = ('season', 'grade', 'is_published')


class LigaChoiceInline(TranslationTabularInline):
    model = LigaChoice
    extra = 4


@admin.register(LigaQuestion)
class LigaQuestionAdmin(TranslationAdmin):
    list_display = ('id', 'test', 'subject', 'question_type', 'score', 'order')
    list_filter = ('test__season', 'test__grade', 'subject', 'question_type')
    inlines = [LigaChoiceInline]

    def _locked(self, obj):
        return bool(obj and obj.test.attempts.exists())

    def has_change_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._locked(obj) and super().has_delete_permission(request, obj)


@admin.register(LigaParticipant)
class LigaParticipantAdmin(admin.ModelAdmin):
    list_display = ('student', 'season', 'grade', 'points', 'joined_at')
    list_filter = ('season', 'grade')
    search_fields = ('student__full_name', 'student__user__phone')
    list_select_related = ('student', 'season', 'grade')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LigaWinner)
class LigaWinnerAdmin(admin.ModelAdmin):
    list_display = ('season', 'grade', 'place', 'student', 'points', 'prize_uz', 'documents_checked', 'is_disqualified')
    list_filter = ('season', 'grade', 'is_disqualified')
    readonly_fields = ('season', 'grade', 'place', 'student', 'points', 'prize_uz', 'prize_ru')

    def has_add_permission(self, request):
        return False


@admin.register(LigaAttempt)
class LigaAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'test', 'status', 'score', 'max_score', 'correct_count',
        'duration_seconds', 'started_at', 'finished_at',
    )
    list_filter = ('test__season', 'test__grade', 'status')
    search_fields = ('student__full_name', 'student__user__phone')
    list_select_related = ('student', 'test', 'test__season', 'test__grade')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
