"""
Admin panel: "AI yechimlar" — savollarni AI yordamida qisqa va batafsil yechish.

  GET  /api/v1/management/ai-solutions/config/                    — AI sozlanganmi (.env), qaysi model
  GET  /api/v1/management/ai-solutions/classes/                   — sinflar
  GET  /api/v1/management/ai-solutions/tree/?class_id=&lang=uz    — fan → bob → mavzu (savollar va yechilganlar soni)
  GET  /api/v1/management/ai-solutions/topics/<id>/?lang=uz       — mavzu savollari va ularning yechimlari
  POST /api/v1/management/ai-solutions/questions/<id>/solve/      — {lang, force} bitta savolni AI bilan yechish

Yechish bittalab chaqiriladi: admin panel mavzudagi savollarni ketma-ket yuborib, progressni o'zi ko'rsatadi.
"""
import html
import re

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_teacher import ai_client
from django_app.app_teacher.models import Chapter, Question, QuestionAISolution, Topic
from django_app.app_user.models import Class, Subject

LANGS = ("uz", "ru")


def _lang(value):
    return value if value in LANGS else "uz"


def _tr(obj, field, lang):
    """modeltranslation maydoni: kerakli tildagisi, bo'lmasa o'zbekchasi."""
    return getattr(obj, f"{field}_{lang}", None) or getattr(obj, f"{field}_uz", None) or getattr(obj, field, None) or ""


def _plain(value):
    """HTML (CKEditor) → oddiy matn; formulalar (\\( \\), $$) o'zgarishsiz qoladi."""
    value = re.sub(r"<img[^>]*>", " [rasm] ", value or "", flags=re.I)
    value = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def _serialize_question(question, lang, solution=None):
    return {
        "id": question.id,
        "level": question.level,
        "type": question.question_type,
        "text": _tr(question, "question_text", lang),
        "text_answer": _tr(question, "correct_text_answer", lang),
        "choices": [
            {
                "letter": choice.letter,
                "text": _tr(choice, "text", lang),
                "image_url": choice.image_url,
                "is_correct": choice.is_correct,
            }
            for choice in question.choices.all()
        ],
        "sub_questions": [
            {"text1": _tr(sub, "text1", lang), "answer": sub.correct_answer, "text2": _tr(sub, "text2", lang)}
            for sub in question.sub_questions.all()
        ],
        "solution": (
            {"data": solution.data, "ai_model": solution.ai_model, "updated_at": solution.updated_at}
            if solution
            else None
        ),
    }


# ---------------------------------------------------------------- AI so'rovi

SYSTEM_PROMPT = {
    "uz": "Sen 5–11-sinf o'quvchilariga matematikani tushuntiradigan tajribali o'qituvchisan. "
    "Yechimni o'zbek tilida (lotin yozuvida), o'quvchi daftarga yozgandek sodda va aniq yozasan.",
    "ru": "Ты опытный учитель математики для 5–11 классов. "
    "Пишешь решение на русском языке — просто и понятно, как ученик в тетради.",
}

FORMAT_RULES = """Javobni FAQAT bitta JSON obyekt ko'rinishida qaytar (markdown, ``` va izohlarsiz):
{
  "parts": [
    {
      "label": "",
      "given": ["v_0 = 4\\\\ \\\\text{m/s}", "t = 3\\\\ \\\\text{s}"],
      "find": "a - ?",
      "short": {
        "formula": "a = \\\\frac{v - v_0}{t}",
        "steps": ["a = \\\\frac{10 - 4}{3} = 2"],
        "answer": "2\\\\ \\\\text{m/s}^2"
      },
      "detailed": {
        "steps": [
          {"title": "1-qadam. Nimani bilamiz?", "text": "Tezlik \\\\(4\\\\) dan \\\\(10\\\\) gacha oshdi ...", "math": ["\\\\Delta v = 10 - 4 = 6"]}
        ],
        "answer": "2\\\\ \\\\text{m/s}^2"
      }
    }
  ],
  "answer": "B) 2 m/s²",
  "conclusion": "Velosipedning tezlanishi \\\\(2\\\\ \\\\text{m/s}^2\\\\) ga teng."
}
Qoidalar:
- Savolda bir nechta kichik misol bo'lsa (1), 2), 3) ...), har biri uchun alohida "parts" elementi yoz va "label" ga raqamini qo'y. Bitta misol bo'lsa — bitta element, "label": "".
- "given", "find", "formula", "steps", "math", "answer" maydonlari — toza LaTeX (\\\\( \\\\) yoki $ belgilarisiz).
- "title", "text", "conclusion" — oddiy matn; matn ichidagi formulalar \\\\( ... \\\\) ichida yoziladi.
- "given" va "find" kerak bo'lmasa (masalan, oddiy hisoblash) bo'sh qoldir: [] va "".
- QISQA yechim: kerakli formula (bo'lsa) va 1–4 qatorli hisob — ortiqcha so'zsiz.
- BATAFSIL yechim: 2–7 qadam. Har qadamda nima qilinayotgani va NIMA UCHUN shunday qilinayotganini tushuntir, oraliq hisoblarni tashlab ketma.
- Yechim berilgan to'g'ri javobga olib kelishi shart. Variantli savolda "answer" ga to'g'ri variant harfini ham yoz.
- Savolda [rasm] bo'lsa va ma'lumot yetmasa, matndagi ma'lumot va to'g'ri javobga tayanib yech."""


def _question_prompt(question, lang):
    lines = [f"Savol ({'o‘zbekcha' if lang == 'uz' else 'ruscha'} yechim yoz):", _plain(_tr(question, "question_text", lang))]
    choices = list(question.choices.all())
    if choices:
        lines.append("\nVariantlar:")
        for choice in choices:
            text = _plain(_tr(choice, "text", lang)) or ("[rasm]" if choice.image_url else "")
            lines.append(f"{choice.letter}) {text}")
        correct = [c.letter for c in choices if c.is_correct]
        if correct:
            lines.append(f"To'g'ri javob: {', '.join(correct)}")
    subs = list(question.sub_questions.all())
    if subs:
        lines.append("\nJavob kataklari (to'g'ri javoblar bilan):")
        for i, sub in enumerate(subs, 1):
            lines.append(f"{i}. {_plain(_tr(sub, 'text1', lang))} [{sub.correct_answer}] {_plain(_tr(sub, 'text2', lang))}".strip())
    text_answer = _plain(_tr(question, "correct_text_answer", lang))
    if text_answer:
        lines.append(f"\nTo'g'ri javob: {text_answer}")
    lines.append("\n" + FORMAT_RULES)
    return "\n".join(lines)


def _as_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value else []


def _normalize(data):
    """AI javobini frontend kutgan shaklga keltiradi (yetishmagan maydonlar bo'sh bo'ladi)."""
    raw_parts = data.get("parts") if isinstance(data, dict) else None
    if not isinstance(raw_parts, list) or not raw_parts:
        raise ai_client.AIError("AI javobida yechim (parts) yo'q")
    parts = []
    for part in raw_parts:
        if not isinstance(part, dict):
            continue
        short = part.get("short") if isinstance(part.get("short"), dict) else {}
        detailed = part.get("detailed") if isinstance(part.get("detailed"), dict) else {}
        steps = []
        for step in detailed.get("steps") or []:
            if isinstance(step, dict):
                steps.append({
                    "title": str(step.get("title") or ""),
                    "text": str(step.get("text") or ""),
                    "math": _as_list(step.get("math")),
                })
            elif step:
                steps.append({"title": "", "text": str(step), "math": []})
        parts.append({
            "label": str(part.get("label") or ""),
            "given": _as_list(part.get("given")),
            "find": str(part.get("find") or ""),
            "short": {
                "formula": str(short.get("formula") or ""),
                "steps": _as_list(short.get("steps")),
                "answer": str(short.get("answer") or ""),
            },
            "detailed": {"steps": steps, "answer": str(detailed.get("answer") or short.get("answer") or "")},
        })
    if not parts:
        raise ai_client.AIError("AI javobida yechim (parts) yo'q")
    return {
        "parts": parts,
        "answer": str(data.get("answer") or ""),
        "conclusion": str(data.get("conclusion") or ""),
    }


def solve_question(question, lang):
    raw = ai_client.complete(SYSTEM_PROMPT[lang], _question_prompt(question, lang))
    return _normalize(ai_client.parse_json(raw))


# ---------------------------------------------------------------- Views

class AISolutionConfigAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        s = ai_client.ai_settings()
        return Response({"configured": ai_client.is_configured(), "model": s["model"], "format": s["format"]})


class AISolutionClassesAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        classes = list(Class.objects.values("id", "name"))
        # "5", "10" kabi nomlar raqam bo'yicha tartiblanadi
        classes.sort(key=lambda c: (0, int(c["name"])) if str(c["name"]).isdigit() else (1, str(c["name"])))
        return Response(classes)


class AISolutionTreeAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        lang = _lang(request.query_params.get("lang"))
        class_id = request.query_params.get("class_id")
        if not class_id:
            return Response({"detail": "class_id kerak"}, status=status.HTTP_400_BAD_REQUEST)

        topics = (
            Topic.objects.filter(chapter__subject__classes_id=class_id)
            .annotate(
                question_count=Count("questions", distinct=True),
                solved_count=Count(
                    "questions__ai_solutions",
                    filter=Q(questions__ai_solutions__lang=lang),
                    distinct=True,
                ),
            )
            .order_by("order", "id")
        )
        chapters = (
            Chapter.objects.filter(subject__classes_id=class_id)
            .prefetch_related(Prefetch("topics", queryset=topics, to_attr="ai_topics"))
            .order_by("order", "id")
        )
        subjects = {
            subject.id: {"id": subject.id, "name": _tr(subject, "name", lang), "active": subject.active, "chapters": []}
            for subject in Subject.objects.filter(classes_id=class_id).order_by("order", "id")
        }
        for chapter in chapters:
            if chapter.subject_id not in subjects:
                continue
            subjects[chapter.subject_id]["chapters"].append({
                "id": chapter.id,
                "name": _tr(chapter, "name", lang),
                "topics": [
                    {
                        "id": topic.id,
                        "name": _tr(topic, "name", lang),
                        "question_count": topic.question_count,
                        "solved_count": topic.solved_count,
                    }
                    for topic in chapter.ai_topics
                ],
            })
        return Response(list(subjects.values()))


def _questions_qs(lang):
    return Question.objects.prefetch_related(
        "choices",
        "sub_questions",
        Prefetch("ai_solutions", queryset=QuestionAISolution.objects.filter(lang=lang), to_attr="lang_solutions"),
    )


class AISolutionTopicAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request, pk):
        lang = _lang(request.query_params.get("lang"))
        topic = get_object_or_404(Topic.objects.select_related("chapter__subject__classes"), pk=pk)
        questions = _questions_qs(lang).filter(topic=topic).order_by("level", "id")
        subject = topic.chapter.subject
        return Response({
            "id": topic.id,
            "name": _tr(topic, "name", lang),
            "chapter": _tr(topic.chapter, "name", lang),
            "subject": _tr(subject, "name", lang) if subject else "",
            "class_name": subject.classes.name if subject and subject.classes else "",
            "questions": [
                _serialize_question(q, lang, q.lang_solutions[0] if q.lang_solutions else None) for q in questions
            ],
        })


class AISolutionSolveAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def post(self, request, pk):
        lang = _lang(request.data.get("lang"))
        force = bool(request.data.get("force"))
        question = get_object_or_404(_questions_qs(lang), pk=pk)

        existing = question.lang_solutions[0] if question.lang_solutions else None
        if existing and not force:
            return Response(_serialize_question(question, lang, existing))

        try:
            data = solve_question(question, lang)
        except ai_client.AIError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        solution, _ = QuestionAISolution.objects.update_or_create(
            question=question,
            lang=lang,
            defaults={"data": data, "ai_model": ai_client.ai_settings()["model"]},
        )
        return Response(_serialize_question(question, lang, solution))
