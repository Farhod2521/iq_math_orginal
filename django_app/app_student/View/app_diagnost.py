from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from django_app.app_user.models import Student, Subject
from django_app.app_student.models import Diagnost_Student, TopicProgress
from django_app.app_teacher.models import Chapter, Topic

from rest_framework import status
from django.db.models import Count

class StudentDiagnostSubjectsAPIView(APIView):
    """
    GET /api/v1/func_student/my-diagnost-subjects/
    Har bir fan: oxirgi diagnostika natijasi (progress_percent), topshirilganmi,
    urinishlar soni, oxirgi sana va zaif (xato ishlangan) mavzular soni.
    Diagnostikalar bitta so'rovda olinadi — fan soniga qarab so'rov ko'paymaydi.
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _score(diagnost):
        try:
            return (diagnost.result or {}).get("result", [{}])[0].get("score")
        except Exception:
            return None

    def get(self, request):
        student = Student.objects.get(user=request.user)

        latest = {}    # subject_id -> eng oxirgi Diagnost_Student
        attempts = {}  # subject_id -> urinishlar soni
        diagnost_qs = (
            Diagnost_Student.objects.filter(student=student)
            .annotate(weak_topics=Count('topic', distinct=True))
            .order_by('subject_id', '-id')
        )
        for d in diagnost_qs:
            attempts[d.subject_id] = attempts.get(d.subject_id, 0) + 1
            latest.setdefault(d.subject_id, d)

        subjects = Subject.objects.all().select_related('classes')
        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            last = latest.get(subject.id)

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": self._score(last) if last else None,  # oxirgi diagnostika bali
                "has_taken_diagnostic": last is not None,
                "attempts_count": attempts.get(subject.id, 0),
                "last_taken_at": last.create_date.strftime("%d.%m.%Y") if last and last.create_date else None,
                "weak_topics_count": last.weak_topics if last else 0,
                "level": last.level if last else None,
            })

        return Response(data)

class SubjectChaptersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi"}, status=404)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"message": "Fan topilmadi"}, status=404)

        # Eng so'nggi diagnostika (agar ko'pi bo'lsa)
        diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).order_by('-id').first()
        if not diagnost:
            return Response({"message": "Ushbu fan bo'yicha diagnostika topilmadi"}, status=404)

        # ✅ Faqat xato bo'lgan boblar
        chapters = diagnost.chapters.all()
        data = [
            {"id": ch.id, "name_uz": ch.name_uz, "name_ru": ch.name_ru}
            for ch in chapters
        ]
        return Response(data)
class ChapterTopicsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi"}, status=404)

        try:
            chapter = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"message": "Bob topilmadi"}, status=404)

        # Ushbu bob qaysi fanga tegishli
        subject = chapter.subject

        # Eng so'nggi diagnostikani topamiz
        diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).order_by('-id').first()
        if not diagnost:
            return Response({"message": "Diagnostika topilmadi"}, status=404)

        # ✅ Faqat shu bobga tegishli va noto'g'ri ishlangan topiclar
        topics = diagnost.topic.filter(chapter=chapter)

        data = [
            {"id": topic.id, "name_uz": topic.name_uz, "name_ru": topic.name_ru}
            for topic in topics
        ]
        return Response(data)
    


class ParentStudentDiagnosticHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 🔒 Faqat parent
        if user.role != "parent":
            return Response(
                {"detail": "Faqat ota-ona uchun ruxsat berilgan"},
                status=status.HTTP_403_FORBIDDEN
            )

        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"detail": "student_id majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        diagnost_dict = {}

        diagnost_list = (
            Diagnost_Student.objects
            .filter(student=student)
            .select_related("subject")
            .prefetch_related("topic")
        )

        for d in diagnost_list:
            subject = d.subject
            subject_id = subject.id

            all_diagnosts = (
                Diagnost_Student.objects
                .filter(student=student, subject=subject)
                .prefetch_related("topic")
                .order_by("id")
            )

            progress_history = []
            topic_counter = {}

            for diag in all_diagnosts:
                # 📊 Ball tarixi
                if diag.result:
                    try:
                        score = diag.result.get("result", [{}])[0].get("score")
                        if score is not None:
                            progress_history.append({
                                "date": diag.create_date.strftime("%Y-%m-%d %H:%M") if diag.create_date else None,
                                "score": score
                            })
                    except Exception:
                        pass

                # 🔁 Takrorlangan mavzular
                for topic in diag.topic.all():
                    topic_counter[topic.id] = topic_counter.get(topic.id, 0) + 1

            repeated_topics = [
                {
                    "id": t.id,
                    "name_uz": t.name_uz,
                    "name_ru": t.name_ru,
                    "repeat_count": topic_counter[t.id]
                }
                for t in Topic.objects.filter(
                    id__in=[tid for tid, count in topic_counter.items() if count >= 3]
                )
            ]

            progress_percent = progress_history[-1]["score"] if progress_history else None
            last_date = progress_history[-1]["date"] if progress_history else None

            diagnost_dict[subject_id] = {
                "progress_history": progress_history,
                "progress_percent": progress_percent,
                "last_date": last_date,
                "repeated_topics": repeated_topics
            }

        subjects = (
            Subject.objects
            .filter(id__in=diagnost_dict.keys())
            .select_related("classes")
        )

        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            info = diagnost_dict[subject.id]

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": info["progress_percent"],
                "progress_history": info["progress_history"],
                "last_date": info["last_date"],
                "has_taken_diagnostic": True,
                "repeated_topics": info["repeated_topics"]
            })

        return Response(data, status=status.HTTP_200_OK)



class StudentDiagnosticHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.get(user=request.user)
        diagnost_dict = {}
        diagnost_list = Diagnost_Student.objects.filter(student=student).select_related('subject')

        for d in diagnost_list:
            subject = d.subject
            subject_id = subject.id

            # Shu fanga tegishli barcha diagnostikalar
            all_diagnosts = Diagnost_Student.objects.filter(
                student=student,
                subject=subject
            ).prefetch_related('topic').order_by('id')

            progress_history = []
            topic_counter = {}

            for diag in all_diagnosts:
                # 🔹 Ball tarixini yig'ish
                if diag.result:
                    try:
                        score = diag.result.get("result", [{}])[0].get("score")
                        if score is not None:
                            progress_history.append({
                                "date": diag.create_date.strftime("%Y-%m-%d %H:%M") if diag.create_date else None,
                                "score": score
                            })
                    except Exception:
                        continue

                # 🔹 Mavzularni hisoblash
                for topic in diag.topic.all():
                    topic_counter[topic.id] = topic_counter.get(topic.id, 0) + 1

            # 🔹 3 martadan ko'p takrorlangan mavzular
            repeated_topics = [
                {
                    "id": t.id,
                    "name_uz": t.name_uz,
                    "name_ru": t.name_ru,
                    "repeat_count": topic_counter[t.id]
                }
                for t in Topic.objects.filter(id__in=[
                    tid for tid, count in topic_counter.items() if count >= 3
                ])
            ]

            # Oxirgi ball va sana
            progress_percent = progress_history[-1]["score"] if progress_history else None
            last_date = progress_history[-1]["date"] if progress_history else None

            diagnost_dict[subject_id] = {
                "progress_history": progress_history,
                "progress_percent": progress_percent,
                "last_date": last_date,
                "repeated_topics": repeated_topics
            }

        # Faqat diagnostika o'tkazilgan fanlar
        subjects = Subject.objects.filter(id__in=diagnost_dict.keys()).select_related('classes')

        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            diagnost_info = diagnost_dict[subject.id]

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": diagnost_info["progress_percent"],
                "progress_history": diagnost_info["progress_history"],
                "last_date": diagnost_info["last_date"],
                "has_taken_diagnostic": True,
                # 🆕 Takrorlangan mavzularni massiv shaklida qaytarish
                "repeated_topics": diagnost_info["repeated_topics"]
            })

        return Response(data)


# ---------------------------------------------------------------------------
# Diagnostika "Xatolar" sahifasi
# ---------------------------------------------------------------------------

def _is_answered(detail):
    """O'quvchi savolga javob berganmi (eski urinishlarda noma'lum — javob berilgan deb olinadi)."""
    if "student_answer" not in detail:
        return True
    answer = detail.get("student_answer")
    if isinstance(answer, list):
        return any(str(item).strip() for item in answer)
    return bool(str(answer or "").strip())


def _diagnost_summary(diag):
    """Bitta urinishning qisqa ma'lumoti (ro'yxat va sahifa sarlavhasi uchun)."""
    result = diag.result or {}
    try:
        summary = (result.get("result") or [{}])[0] or {}
    except Exception:
        summary = {}
    questions = result.get("question") or []
    total = summary.get("total_answers")
    correct = summary.get("correct_answers")
    if total is None:
        total = len(questions)
    if correct is None:
        correct = sum(1 for q in questions if q.get("answer"))
    unanswered = sum(1 for q in questions if not q.get("answer") and not _is_answered(q))
    return {
        "id": diag.id,
        "date": diag.create_date.strftime("%d.%m.%Y %H:%M") if diag.create_date else None,
        "level": diag.level,
        "score": summary.get("score", 0) or 0,
        "total_answers": total,
        "correct_answers": correct,
        # Xato = javob berilgan, lekin noto'g'ri; javob berilmaganlar alohida
        "wrong_answers": max(0, (total or 0) - (correct or 0) - unanswered),
        "unanswered_answers": unanswered,
        "duration_seconds": result.get("duration_seconds"),
        # Eski urinishlarda o'quvchi javobi saqlanmagan
        "has_answers": any("student_answer" in q for q in questions),
    }


def _subject_payload(subject):
    class_name = subject.classes.name if subject and subject.classes else ""
    return {
        "id": subject.id,
        "name_uz": subject.name_uz,
        "name_ru": subject.name_ru,
        "class_name": class_name,
    } if subject else None


class StudentDiagnostAttemptsAPIView(APIView):
    """
    GET /api/v1/func_student/my-diagnost/subjects/<subject_id>/attempts/
    Fan bo'yicha barcha diagnostika urinishlari (yangisi birinchi).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        student = get_object_or_404(Student, user=request.user)
        subject = get_object_or_404(Subject.objects.select_related('classes'), id=subject_id)
        attempts = Diagnost_Student.objects.filter(student=student, subject=subject).order_by('-id')
        return Response({
            "subject": _subject_payload(subject),
            "attempts": [_diagnost_summary(diag) for diag in attempts],
        })


class StudentDiagnostMistakesAPIView(APIView):
    """
    GET /api/v1/func_student/my-diagnost/<diagnost_id>/mistakes/
    Bitta urinishdagi savollar: savol matni, variantlar, o'quvchi belgilagan javob
    va to'g'ri javob. Faqat o'quvchining o'z diagnostikasi qaytariladi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, diagnost_id):
        from django.db.models import Prefetch
        from django_app.app_teacher.models import Question, Choice

        student = get_object_or_404(Student, user=request.user)
        diag = get_object_or_404(
            Diagnost_Student.objects.select_related('subject__classes'),
            id=diagnost_id,
            student=student,
        )

        details = (diag.result or {}).get("question") or []
        question_ids = [d.get("question_id") for d in details if d.get("question_id")]
        questions = {
            q.id: q
            for q in Question.objects.filter(id__in=question_ids)
            .select_related('topic__chapter')
            .prefetch_related(Prefetch('choices', queryset=Choice.objects.order_by('letter', 'id')), 'sub_questions')
        }

        items = []
        for number, detail in enumerate(details, start=1):
            question = questions.get(detail.get("question_id"))
            if not question:
                continue  # savol bazadan o'chirilgan
            has_answer = "student_answer" in detail
            student_answer = detail.get("student_answer")
            q_type = question.question_type
            item = {
                "number": number,
                "question_id": question.id,
                "question_type": q_type,
                "question_text_uz": question.question_text_uz,
                "question_text_ru": question.question_text_ru,
                "topic_uz": question.topic.name_uz if question.topic else "",
                "topic_ru": question.topic.name_ru if question.topic else "",
                "is_correct": bool(detail.get("answer")),
                "has_answer": has_answer,
                "is_answered": _is_answered(detail),
            }

            if q_type in ("choice", "image_choice"):
                selected = set(student_answer or []) if has_answer else set()
                item["choices"] = [
                    {
                        "id": choice.id,
                        "letter": choice.letter,
                        "text_uz": choice.text_uz,
                        "text_ru": choice.text_ru,
                        "image_url": choice.image_url,
                        "is_correct": choice.is_correct,
                        "is_selected": choice.id in selected,
                    }
                    for choice in question.choices.all()
                ]
            elif q_type == "composite":
                answers = student_answer if has_answer and isinstance(student_answer, list) else []
                item["sub_questions"] = [
                    {
                        "id": sub.id,
                        "text1_uz": sub.text1_uz or "",
                        "text1_ru": sub.text1_ru or "",
                        "text2_uz": "" if sub.text2_uz in (None, "undefined") else sub.text2_uz,
                        "text2_ru": "" if sub.text2_ru in (None, "undefined") else sub.text2_ru,
                        "correct_answer": sub.correct_answer,
                        "student_answer": answers[index] if index < len(answers) else None,
                    }
                    for index, sub in enumerate(question.sub_questions.all())
                ]
            else:  # text
                item["student_answer"] = student_answer if has_answer else None
                item["correct_answer_uz"] = question.correct_text_answer_uz or ""
                item["correct_answer_ru"] = question.correct_text_answer_ru or ""

            items.append(item)

        # "Tahlil" (AI yechim) tugmasi admin paneldagi fanlar sozlamasiga bo'ysunadi
        from django_app.app_management.models import SolutionStatus
        solution_status = SolutionStatus.objects.first()

        return Response({
            "subject": _subject_payload(diag.subject),
            "solution_enabled": bool(solution_status and solution_status.subject_is_active),
            "attempt": _diagnost_summary(diag),
            "questions": items,
        })
