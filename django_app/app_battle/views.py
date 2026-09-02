from collections import defaultdict

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_app.app_user.models import Student, Class, Subject

from . import matchmaking
from .models import BattleRoom, BattleRating, BattleEloLog, level_for_elo, level_progress
from .serializers import RoomCreateSerializer, RoomJoinSerializer, serialize_room_snapshot


def _get_student(request):
    return Student.objects.filter(user=request.user).first()


class CreateRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = _get_student(request)
        if not student:
            return Response({"message": "O'quvchi topilmadi"}, status=404)

        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        grade = get_object_or_404(Class, id=data['grade_id'])
        subjects = list(Subject.objects.filter(id__in=data['subject_ids'], classes=grade))
        if not subjects:
            return Response({"message": "Tanlangan fanlar shu sinfga tegishli emas"}, status=400)

        room, matched = matchmaking.find_or_create_room(
            student,
            grade=grade, subjects=subjects,
            question_count=data['question_count'], seconds_per_question=data['seconds_per_question'],
        )
        return Response({
            "matched": matched,
            "room": serialize_room_snapshot(room, student),
        }, status=status.HTTP_201_CREATED)


class JoinRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = _get_student(request)
        if not student:
            return Response({"message": "O'quvchi topilmadi"}, status=404)

        serializer = RoomJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            room, matched = matchmaking.join_room_by_code(student, serializer.validated_data['code'])
        except matchmaking.RoomFull as exc:
            return Response({"message": str(exc)}, status=400)
        except matchmaking.RoomNotJoinable as exc:
            return Response({"message": str(exc)}, status=400)

        return Response({"matched": matched, "room": serialize_room_snapshot(room, student)})


class RoomDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        student = _get_student(request)
        room = get_object_or_404(BattleRoom, id=room_id)
        if not room.participants.filter(student=student).exists():
            return Response({"message": "Sizda ruxsat yo'q"}, status=403)
        return Response(serialize_room_snapshot(room, student))


class CancelRoomAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        student = _get_student(request)
        room = get_object_or_404(BattleRoom, id=room_id)
        try:
            room = matchmaking.cancel_room(student, room)
        except matchmaking.RoomNotJoinable as exc:
            return Response({"message": str(exc)}, status=400)
        return Response(serialize_room_snapshot(room, student))


class MyRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return Response({"message": "O'quvchi topilmadi"}, status=404)
        rating, _ = BattleRating.objects.get_or_create(student=student)
        progress = None if rating.is_in_placement else level_progress(rating.elo)
        return Response({
            "elo": rating.elo,
            "level": rating.level,
            "is_in_placement": rating.is_in_placement,
            "matches_played": rating.matches_played,
            "matches_left_for_placement": max(0, BattleRating.PLACEMENT_MATCHES - rating.matches_played),
            "wins": rating.wins,
            "losses": rating.losses,
            "draws": rating.draws,
            "win_streak": rating.win_streak,
            "best_elo": rating.best_elo,
            "level_progress": progress,
        })


class GradeStatsAPIView(APIView):
    """Real, platform-wide per-grade activity numbers (total finished
    battles + win rate) — powers the grade-picker cards on the setup page.
    Not personal history: a fresh student picking an untried grade still
    sees genuine numbers, not fabricated ones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        totals = {
            row['grade_id']: row['total']
            for row in BattleRoom.objects.filter(status=BattleRoom.STATUS_FINISHED)
            .values('grade_id').annotate(total=Count('id'))
        }

        win_counts = defaultdict(int)
        decided_counts = defaultdict(int)
        for row in (
            BattleEloLog.objects.filter(room__isnull=False)
            .exclude(result='draw')
            .values('room__grade_id', 'result')
            .annotate(count=Count('id'))
        ):
            grade_id = row['room__grade_id']
            decided_counts[grade_id] += row['count']
            if row['result'] == 'win':
                win_counts[grade_id] += row['count']

        results = []
        for grade in Class.objects.all().order_by('id'):
            decided = decided_counts.get(grade.id, 0)
            win_rate = round((win_counts.get(grade.id, 0) / decided) * 100) if decided else 0
            results.append({
                "grade_id": grade.id,
                "name": grade.name,
                "total_matches": totals.get(grade.id, 0),
                "win_rate": win_rate,
            })
        return Response({"results": results})


class LeaderboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        top_count = int(request.query_params.get('top_count', 50))
        ratings = (
            BattleRating.objects.filter(matches_played__gte=BattleRating.PLACEMENT_MATCHES)
            .select_related('student', 'student__class_name', 'student__class_name__classes')
            .order_by('-elo')[:top_count]
        )
        results = []
        for rank, rating in enumerate(ratings, start=1):
            student = rating.student
            class_name = getattr(getattr(student, 'class_name', None), 'classes', None)
            results.append({
                "rank": rank,
                "student_id": student.id,
                "full_name": student.full_name,
                "class_uz": getattr(class_name, 'name', ''),
                "class_ru": getattr(class_name, 'name', ''),
                "elo": rating.elo,
                "level": rating.level,
                "wins": rating.wins,
                "losses": rating.losses,
                "draws": rating.draws,
            })
        return Response({"results": results})


class HistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return Response({"message": "O'quvchi topilmadi"}, status=404)

        logs = BattleEloLog.objects.filter(student=student).select_related('room').prefetch_related('room__subjects')[:100]
        results = []
        for log in logs:
            room = log.room
            opponent = None
            if room:
                opponent_participant = room.participants.exclude(student=student).first()
                if opponent_participant:
                    opponent = {
                        "name": opponent_participant.display_name,
                        "level": level_for_elo(opponent_participant.elo_before),
                    }
            results.append({
                "room_id": room.id if room else None,
                "subjects": [s.name for s in room.subjects.all()] if room else [],
                "result": log.result,
                "elo_change": log.elo_change,
                "elo_after": log.elo_after,
                "is_placement": log.is_placement,
                "is_placement_reveal": log.is_placement and log.elo_after > 0,
                "opponent": opponent,
                "created_at": log.created_at,
            })

        rating, _ = BattleRating.objects.get_or_create(student=student)
        total = rating.wins + rating.losses + rating.draws
        win_rate = round((rating.wins / total) * 100, 1) if total else 0.0

        return Response({
            "stats": {
                "total_matches": total,
                "wins": rating.wins,
                "losses": rating.losses,
                "draws": rating.draws,
                "win_rate": win_rate,
            },
            "results": results,
        })


class EloHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return Response({"message": "O'quvchi topilmadi"}, status=404)

        logs = (
            BattleEloLog.objects.filter(student=student)
            .exclude(is_placement=True, elo_after=0)  # skip hidden placement-calibration rows
            .order_by('created_at')
            .values('created_at', 'elo_after')
        )
        return Response({"results": list(logs)})
