"""
Admin panel: "AI yechimlar" — savollarni AI yordamida qisqa va batafsil yechish.

  GET  /api/v1/management/ai-solutions/config/                       — AI sozlanganmi (.env), qaysi model
  GET  /api/v1/management/ai-solutions/classes/                      — sinflar
  GET  /api/v1/management/ai-solutions/tree/?class_id=&lang=uz       — fan → bob → mavzu (savollar va yechilganlar soni)
  GET  /api/v1/management/ai-solutions/subjects/<id>/queue/          — butun kitob savollari tartib bilan (yechish navbati)
  GET  /api/v1/management/ai-solutions/topics/<id>/?lang=uz          — mavzu savollari va ularning yechimlari
  POST /api/v1/management/ai-solutions/questions/<id>/solve/         — {lang, force} savolni o'zbekcha yechish
  POST /api/v1/management/ai-solutions/questions/<id>/translate/     — {lang, force} o'zbekcha yechimni rus tiliga o'girish
  POST /api/v1/management/ai-solutions/questions/<id>/digitize/      — {lang} matndagi base64 rasm-formulalarni LaTeX ga aylantirish

Har bir misol bir marta (o'zbekcha) yechiladi, ruscha yechim — uning tarjimasi: hisob va formulalar bir xil qoladi.
Yechish bittalab chaqiriladi: admin panel savollarni ketma-ket yuborib, progressni o'zi ko'rsatadi.

Ko'p savollarda misol matn emas, base64 rasm (<img src="data:image/png;base64,...">) bo'lib saqlangan.
Yechishdan oldin bunday rasmlar AI ga ko'rsatiladi: formula bo'lsa — LaTeX ga aylantirilib bazaga yoziladi
(asl HTML QuestionImageBackup da qoladi), chizma bo'lsa — rasm joyida qoladi va yechishda AI ga ilova qilinadi.
"""
import html
import json
import re

from django.db import transaction
from django.db.models import BooleanField, Case, Count, Exists, OuterRef, Prefetch, Q, When
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_teacher import ai_client
from django_app.app_teacher.models import Chapter, Choice, Question, QuestionAISolution, QuestionImageBackup, Topic
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


# ---------------------------------------------------------------- Rasmdagi formulalar

# Matn ichidagi base64 rasm; AI chizma deb topganlari data-ai-figure bilan belgilanadi va qayta so'ralmaydi
_DATA_IMG = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*(["'])data:(image/[\w.+-]+);base64,([^"']+)\1[^>]*>""", re.I)
_SUPPORTED_MEDIA = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGES = 8


def _media_type(value):
    value = value.lower()
    return "image/jpeg" if value in ("image/jpg", "image/pjpeg") else value


def _image_data(match):
    return re.sub(r"\s+", "", match.group(3))


def _pending_images(value):
    """Hali AI ga ko'rsatilmagan (formula yoki chizma ekani noma'lum) base64 rasmlar."""
    return [
        m for m in _DATA_IMG.finditer(value or "")
        if "data-ai-figure" not in m.group(0) and _media_type(m.group(2)) in _SUPPORTED_MEDIA
    ]


def _text_fields(question):
    """Rasm bo'lishi mumkin bo'lgan matn maydonlari: (obyekt, maydon, zaxiradagi nomi)."""
    for lang in LANGS:
        yield question, f"question_text_{lang}", f"question_text_{lang}"
    for choice in question.choices.all():
        for lang in LANGS:
            yield choice, f"text_{lang}", f"choice:{choice.id}:text_{lang}"


def _has_pending_images(question):
    return any(_pending_images(getattr(obj, attr, "")) for obj, attr, _ in _text_fields(question))


def _serialize_question(question, lang, solution=None):
    return {
        "id": question.id,
        "has_images": _has_pending_images(question),
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

DIGITIZE_SYSTEM = (
    "Sen darslikdagi matematik misollar rasmlarini aniq LaTeX ga ko'chiradigan yordamchisan. "
    "Rasmdagi hech bir son, belgi yoki qavsni o'zgartirmaysan, qo'shmaysan va tashlab ketmaysan."
)

DIGITIZE_RULES = """Yuqorida savol matnidagi __COUNT__ ta rasm berilgan (tartib bilan). Savol matni (rasmlar o'rnida [rasm N]):
__TEXT__

Har bir rasm uchun aniqla:
- Rasmda faqat matematik ifoda (kasr, son, tenglama, misol, yulduzchali misol, ildiz, daraja va h.k.) bo'lsa —
  uni LaTeX ga ko'chir: {"kind": "math", "latex": "..."}
  * kasrlar \\dfrac{...}{...}, ko'paytirish nuqtasi \\cdot, ko'paytirish xochi \\times, bo'lish \\div;
  * yulduzcha / bo'sh katak — \\ast yoki \\square (rasmdagidek); aralash son 2\\dfrac{1}{3} ko'rinishida;
  * bir nechta qator bo'lsa — \\begin{array}{l} ... \\\\ ... \\end{array};
  * \\( \\) yoki $ belgilarisiz, faqat ifodaning o'zi.
- Rasmda chizma (geometrik shakl, grafik, son o'qi, jadval, rasm-surat) bo'lsa — {"kind": "figure"}.

Javobni FAQAT JSON ko'rinishida qaytar (markdown, ``` va izohlarsiz), rasmlar soni va tartibi aynan bir xil:
{"images": [{"kind": "math", "latex": "\\dfrac{334 \\cdot 123 + 27}{335 \\cdot 123 - 102}"}, {"kind": "figure"}]}"""


def digitize_question(question):
    """
    Savol va variantlar matnidagi base64 rasmlarni AI ga ko'rsatadi: formulalar LaTeX ga aylantirilib
    bazaga yoziladi (asl HTML zaxiraga olinadi), chizmalar data-ai-figure bilan belgilanadi.
    Bir xil rasm (o'zbekcha va ruscha matnda) bir marta so'raladi. O'zgargan maydonlar soni qaytadi.
    """
    fields = list(_text_fields(question))
    unique = {}  # base64 → media type (tartib — AI ga yuborilish tartibi)
    for obj, attr, _ in fields:
        for m in _pending_images(getattr(obj, attr, "")):
            unique.setdefault(_image_data(m), _media_type(m.group(2)))
    if not unique:
        return 0

    numbers = {data: n for n, data in enumerate(unique, 1)}
    context = _DATA_IMG.sub(lambda m: f" [rasm {numbers.get(_image_data(m), '')}] ", _tr(question, "question_text", "uz"))
    prompt = DIGITIZE_RULES.replace("__COUNT__", str(len(unique))).replace("__TEXT__", _plain(context))
    images = [{"media_type": media, "data": data} for data, media in unique.items()]
    result = ai_client.parse_json(ai_client.complete(DIGITIZE_SYSTEM, prompt, images=images))
    items = result.get("images") if isinstance(result, dict) else None
    if not isinstance(items, list) or len(items) != len(unique):
        raise ai_client.AIError("AI rasmlar sonini noto'g'ri qaytardi")

    replacements = {}  # base64 → formula HTML yoki None (chizma)
    for data, item in zip(unique, items):
        latex = str(item.get("latex") or "").strip() if isinstance(item, dict) else ""
        latex = latex.removeprefix("\\(").removesuffix("\\)").strip("$ \n")
        if isinstance(item, dict) and item.get("kind") == "math" and latex and len(latex) < 3000:
            replacements[data] = "\\(\\displaystyle " + html.escape(latex, quote=False) + "\\)"
        else:
            replacements[data] = None

    def replace(m):
        if "data-ai-figure" in m.group(0) or _image_data(m) not in replacements:
            return m.group(0)
        new = replacements[_image_data(m)]
        return new if new is not None else re.sub(r"^<img\b", '<img data-ai-figure="1"', m.group(0), flags=re.I)

    changed = 0
    with transaction.atomic():
        for obj, attr, backup_name in fields:
            old = getattr(obj, attr, None)
            if not old or not _pending_images(old):
                continue
            new = _DATA_IMG.sub(replace, old)
            if new == old:
                continue
            QuestionImageBackup.objects.create(question=question, field=backup_name, original=old)
            setattr(obj, attr, new)
            obj.save(update_fields=[attr])
            changed += 1
    return changed


def _solver_images(question):
    """Yechishda AI ga ilova qilinadigan rasmlar: matnda qolgan chizmalar va variant rasmlari (http)."""
    images, seen = [], set()
    for obj, attr, _ in _text_fields(question):
        if not attr.endswith("_uz"):
            continue
        for m in _DATA_IMG.finditer(getattr(obj, attr, "") or ""):
            data, media = _image_data(m), _media_type(m.group(2))
            if media in _SUPPORTED_MEDIA and data not in seen:
                seen.add(data)
                images.append({"media_type": media, "data": data})
    for choice in question.choices.all():
        url = choice.image_url or ""
        if url.startswith(("http://", "https://")) and url not in seen:
            seen.add(url)
            images.append({"url": url})
    return images[:MAX_IMAGES]

SYSTEM_PROMPT = (
    "Sen 1–11-sinf o'quvchilariga matematikani tushuntiradigan tajribali o'qituvchisan. "
    "Yechimni o'zbek tilida (lotin yozuvida), o'quvchi daftarga yozgandek sodda va aniq yozasan."
)

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
        "figure": null,
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
- Savolda [rasm] bo'lsa — u so'rovga ilova qilingan rasm (chizma); undagi ma'lumotdan foydalan.
  Rasm ilova qilinmagan yoki ma'lumot yetmasa, matndagi ma'lumot va to'g'ri javobga tayanib yech.

CHIZMA ("detailed.figure") — faqat chizma o'quvchiga tushunishda HAQIQATAN yordam beradigan misollarda
(funksiya grafigi, geometrik shakl, son o'qi, harakat yoki jarayon sxemasi). Oddiy hisoblash, kasrlar,
tenglamalarda chizma kerak emas — "figure": null. Ikki xil chizma bor:
1) Funksiya grafigi:
   {"type": "graph", "x": [-5, 5], "y": [-4, 6],
    "functions": [{"expr": "2*x + 1", "label": "y = 2x + 1"}],
    "points": [{"x": 0, "y": 1, "label": "A(0; 1)"}]}
   "expr" — faqat x, sonlar, + - * / ^, qavslar, sqrt, abs, sin, cos, tan, ln, log, exp, pi. Ko'pi bilan 3 ta funksiya.
2) Boshqa chizma (uchburchak, aylana, son o'qi, sxema):
   {"type": "svg", "svg": "<svg viewBox=\\"0 0 400 260\\" xmlns=\\"http://www.w3.org/2000/svg\\">...</svg>"}
   Faqat line, polyline, polygon, path, circle, ellipse, rect, text elementlari; stroke="currentColor",
   fill="none" (matn uchun fill="currentColor"), stroke-width="2", matn font-size="18". style, script, rasm ishlatma.
   Chizma aniq bo'lsin: nuqtalar, uzunliklar va burchaklar yechimdagi qiymatlarga mos kelsin."""

TRANSLATE_SYSTEM = (
    "Sen matematika yechimlarini o'zbek tilidan rus tiliga tarjima qiladigan tarjimonsan. "
    "Matematik mazmunni o'zgartirmaysan — faqat so'zlarni tarjima qilasan."
)

TRANSLATE_RULES = """Quyidagi JSON — o'zbekcha matematik yechim. Uni xuddi shu tuzilishdagi JSON qilib rus tiliga o'gir:
- "title", "text", "conclusion", "answer" va "label" dagi o'zbekcha so'zlarni ruschaga tarjima qil.
- LaTeX formulalarni, sonlarni va hisoblarni o'zgartirma. Faqat \\\\text{...} ichidagi o'zbekcha so'zlarni tarjima qil
  (masalan \\\\text{ta} → \\\\text{шт.}); birliklar ruscha yoziladi (m/s → м/с, sm → см, kg → кг).
- Elementlar soni va tartibi aynan bir xil qolsin. Hech narsa qo'shma va o'chirma.
- Javobni FAQAT JSON ko'rinishida qaytar (markdown, ``` va izohlarsiz)."""


def _question_prompt(question):
    lines = ["Savol:", _plain(_tr(question, "question_text", "uz"))]
    choices = list(question.choices.all())
    if choices:
        lines.append("\nVariantlar:")
        for choice in choices:
            text = _plain(_tr(choice, "text", "uz")) or ("[rasm]" if choice.image_url else "")
            lines.append(f"{choice.letter}) {text}")
        correct = [c.letter for c in choices if c.is_correct]
        if correct:
            lines.append(f"To'g'ri javob: {', '.join(correct)}")
    subs = list(question.sub_questions.all())
    if subs:
        lines.append("\nJavob kataklari (to'g'ri javoblar bilan):")
        for i, sub in enumerate(subs, 1):
            lines.append(f"{i}. {_plain(_tr(sub, 'text1', 'uz'))} [{sub.correct_answer}] {_plain(_tr(sub, 'text2', 'uz'))}".strip())
    text_answer = _plain(_tr(question, "correct_text_answer", "uz"))
    if text_answer:
        lines.append(f"\nTo'g'ri javob: {text_answer}")
    lines.append("\n" + FORMAT_RULES)
    return "\n".join(lines)


def _as_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value else []


def _num(value, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if -1e6 < number < 1e6 else default


def _range(value, default):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        low, high = _num(value[0], default[0]), _num(value[1], default[1])
        if low < high:
            return [low, high]
    return list(default)


_SVG_FORBIDDEN = re.compile(r"<\s*(script|foreignObject|image|iframe|use|style)\b|\son\w+\s*=|javascript:|href\s*=", re.I)


def _normalize_figure(figure):
    """Chizmani tekshiradi: grafik — raqamli parametrlar, svg — xavfli teglarsiz. Yaroqsiz bo'lsa None."""
    if not isinstance(figure, dict):
        return None
    if figure.get("type") == "graph":
        functions = [
            {"expr": str(f.get("expr"))[:120], "label": str(f.get("label") or "")[:60]}
            for f in (figure.get("functions") or [])[:3]
            if isinstance(f, dict) and f.get("expr")
        ]
        points = [
            {"x": _num(p.get("x"), 0), "y": _num(p.get("y"), 0), "label": str(p.get("label") or "")[:40]}
            for p in (figure.get("points") or [])[:12]
            if isinstance(p, dict)
        ]
        if not functions and not points:
            return None
        return {
            "type": "graph",
            "x": _range(figure.get("x"), (-5, 5)),
            "y": _range(figure.get("y"), (-5, 5)),
            "functions": functions,
            "points": points,
        }
    if figure.get("type") == "svg":
        svg = str(figure.get("svg") or "").strip()
        if svg.startswith("<svg") and svg.endswith("</svg>") and len(svg) < 20000 and not _SVG_FORBIDDEN.search(svg):
            return {"type": "svg", "svg": svg}
    return None


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
            "detailed": {
                "figure": _normalize_figure(detailed.get("figure") or part.get("figure")),
                "steps": steps,
                "answer": str(detailed.get("answer") or short.get("answer") or ""),
            },
        })
    if not parts:
        raise ai_client.AIError("AI javobida yechim (parts) yo'q")
    return {
        "parts": parts,
        "answer": str(data.get("answer") or ""),
        "conclusion": str(data.get("conclusion") or ""),
    }


def solve_question(question):
    """Savolni o'zbek tilida yechadi."""
    raw = ai_client.complete(SYSTEM_PROMPT, _question_prompt(question), images=_solver_images(question))
    return _normalize(ai_client.parse_json(raw))


def translate_solution(data):
    """O'zbekcha yechimni ruschaga o'giradi. Chizmalar tarjimaga yuborilmaydi — o'zbekchasidan ko'chiriladi."""
    figures = [part["detailed"].get("figure") for part in data["parts"]]
    payload = {
        **data,
        "parts": [{**part, "detailed": {k: v for k, v in part["detailed"].items() if k != "figure"}} for part in data["parts"]],
    }
    prompt = TRANSLATE_RULES + "\n\n" + json.dumps(payload, ensure_ascii=False)
    translated = _normalize(ai_client.parse_json(ai_client.complete(TRANSLATE_SYSTEM, prompt)))
    if len(translated["parts"]) != len(figures):
        raise ai_client.AIError("Tarjimada yechim qismlari soni o'zgarib ketdi")
    for part, figure in zip(translated["parts"], figures):
        part["detailed"]["figure"] = figure
    return translated


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


def _question_response(pk, lang):
    question = get_object_or_404(_questions_qs(lang), pk=pk)
    return Response(_serialize_question(question, lang, question.lang_solutions[0] if question.lang_solutions else None))


class AISolutionSolveAPIView(APIView):
    """Savolni o'zbekcha yechadi (force — qaytadan; eski ruscha tarjima o'chiriladi). Javob — so'ralgan tilda."""

    permission_classes = [IsTeacherOrSuperAdmin]

    def post(self, request, pk):
        lang = _lang(request.data.get("lang"))
        force = bool(request.data.get("force"))
        question = get_object_or_404(_questions_qs("uz"), pk=pk)

        if force or not question.lang_solutions:
            try:
                data = solve_question(question)
            except ai_client.AIError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
            QuestionAISolution.objects.update_or_create(
                question=question,
                lang="uz",
                defaults={"data": data, "ai_model": ai_client.ai_settings()["model"]},
            )
            # Yechim yangilandi — eski tarjima endi mos emas
            QuestionAISolution.objects.filter(question=question, lang="ru").delete()
        return _question_response(pk, lang)


class AISolutionDigitizeAPIView(APIView):
    """Savol matnidagi base64 rasm-formulalarni LaTeX ga aylantirib bazaga yozadi. Javob — so'ralgan tilda."""

    permission_classes = [IsTeacherOrSuperAdmin]

    def post(self, request, pk):
        lang = _lang(request.data.get("lang"))
        question = get_object_or_404(Question.objects.prefetch_related("choices"), pk=pk)
        try:
            digitize_question(question)
        except ai_client.AIError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return _question_response(pk, lang)


class AISolutionTranslateAPIView(APIView):
    """O'zbekcha yechimni rus tiliga o'giradi (o'zbekchasi bo'lmasa — 400)."""

    permission_classes = [IsTeacherOrSuperAdmin]

    def post(self, request, pk):
        lang = _lang(request.data.get("lang"))
        force = bool(request.data.get("force"))
        question = get_object_or_404(Question, pk=pk)
        source = QuestionAISolution.objects.filter(question=question, lang="uz").first()
        if not source:
            return Response({"detail": "Avval o'zbekcha yechim kerak"}, status=status.HTTP_400_BAD_REQUEST)

        if force or not QuestionAISolution.objects.filter(question=question, lang="ru").exists():
            try:
                data = translate_solution(source.data)
            except ai_client.AIError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
            QuestionAISolution.objects.update_or_create(
                question=question,
                lang="ru",
                defaults={"data": data, "ai_model": ai_client.ai_settings()["model"]},
            )
        return _question_response(pk, lang)


class AISolutionSubjectQueueAPIView(APIView):
    """Butun kitob (fan) savollari — bob, mavzu, daraja tartibida; har birida qaysi tilda yechim borligi."""

    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        solved = {}
        for question_id, lang in QuestionAISolution.objects.filter(
            question__topic__chapter__subject=subject
        ).values_list("question_id", "lang"):
            solved.setdefault(question_id, set()).add(lang)

        # Matnida base64 rasm bor savollar — yechishdan oldin rasmlar formulaga aylantiriladi
        choice_image = Choice.objects.filter(question=OuterRef("pk")).filter(
            Q(text_uz__contains="data:image") | Q(text_ru__contains="data:image")
        )
        has_image = Q(question_text_uz__contains="data:image") | Q(question_text_ru__contains="data:image") | Exists(choice_image)
        questions = (
            Question.objects.filter(topic__chapter__subject=subject)
            .annotate(images=Case(When(has_image, then=True), default=False, output_field=BooleanField()))
            .order_by("topic__chapter__order", "topic__chapter_id", "topic__order", "topic_id", "level", "id")
            .values("id", "topic_id", "topic__chapter_id", "images")
        )
        return Response([
            {
                "id": q["id"],
                "topic_id": q["topic_id"],
                "chapter_id": q["topic__chapter_id"],
                "uz": "uz" in solved.get(q["id"], ()),
                "ru": "ru" in solved.get(q["id"], ()),
                "images": q["images"],
            }
            for q in questions
        ])
