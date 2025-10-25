from openai import OpenAI
from django_app.app_teacher.models import (
    Subject, Chapter, Topic,
    GeneratedQuestionOpenAi, GeneratedChoiceOpenAi, GeneratedSubQuestionOpenAi
)
import os

client = OpenAI(api_key=os.getenv("OPENAI"))


def generate_topic_questions(subject_id: int, chapter_id: int, topic_id: int):
    topic = Topic.objects.select_related("chapter", "chapter__subject").get(id=topic_id)
    subject = topic.chapter.subject
    topic_name = topic.name

    total_generated = 0

    # ✅ 1️⃣ TEXT SAVOLLAR (5 ta)
    for i in range(5):
        prompt = f"""
        Sen {subject.name} fanidan o‘quv test generatorisan.
        Mavzu: "{topic_name}"
        - Savol turi: text (matnli javob)
        - Foydalanuvchidan aniq javob kutiladi (raqam, so‘z yoki formula)
        - Savol aniq, qisqa va mantiqiy bo‘lsin.
        Natijani quyidagi formatda 2 tilda qaytar:
        🇺🇿 Uzbekcha: ...
        🇷🇺 Русский: ...
        """

        response = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = response.output[0].content[0].text.strip()

        # AI javobini 2 tilda ajratamiz
        uz_text, ru_text = extract_bilingual(text)

        GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="text",
            generated_text_uz=uz_text,
            generated_text_ru=ru_text
        )
        total_generated += 1

    # ✅ 2️⃣ CHOICE SAVOLLAR (3 ta)
    for i in range(3):
        prompt = f"""
        Sen {subject.name} fanidan test tuzuvchi AI assistantisan.
        Mavzu: "{topic_name}"
        Quyidagi formatda yangi test savolini yarat:
        🇺🇿 Uzbekcha savol:
        Savol: ...
        A) ...
        B) ...
        C) ...
        D) ...
        To‘g‘ri javob: (A, B, C yoki D dan biri)

        🇷🇺 Русский вариант:
        Вопрос:
        A) ...
        B) ...
        C) ...
        D) ...
        Правильный ответ: ...
        """

        content = client.responses.create(model="gpt-4o-mini", input=prompt).output[0].content[0].text.strip()

        # Bo‘lib olish
        uz_block, ru_block = split_uz_ru(content)
        gen_q = GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="choice",
            generated_text_uz=extract_question_line(uz_block),
            generated_text_ru=extract_question_line(ru_block)
        )

        # Variantlar
        add_choice_variants(gen_q, uz_block, lang="uz")
        add_choice_variants(gen_q, ru_block, lang="ru")

        total_generated += 1

    # ✅ 3️⃣ COMPOSITE SAVOLLAR (2 ta)
    for i in range(2):
        prompt = f"""
        Sen {subject.name} fanidan o‘quv mashq generatorisan.
        Mavzu: "{topic_name}"
        Quyidagi formatda misol yarat 2 tilda:
        🇺🇿 Uzbekcha: text1, correct_answer, text2
        🇷🇺 Русский: text1, correct_answer, text2
        Masalan:
        🇺🇿: 5 + 3, 8, =
        🇷🇺: 5 + 3, 8, =
        """

        content = client.responses.create(model="gpt-4o-mini", input=prompt).output[0].content[0].text.strip()

        uz_part, ru_part = split_uz_ru(content)
        uz_parts = [p.strip() for p in uz_part.split(",")]
        ru_parts = [p.strip() for p in ru_part.split(",")]

        gen_q = GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="composite",
            generated_text_uz=f"{topic_name} uchun mashq",
            generated_text_ru=f"Упражнение по теме {topic_name}"
        )

        GeneratedSubQuestionOpenAi.objects.create(
            generated_question=gen_q,
            text1_uz=uz_parts[0] if len(uz_parts) > 0 else "",
            correct_answer_uz=uz_parts[1] if len(uz_parts) > 1 else "",
            text2_uz=uz_parts[2] if len(uz_parts) > 2 else "",
            text1_ru=ru_parts[0] if len(ru_parts) > 0 else "",
            correct_answer_ru=ru_parts[1] if len(ru_parts) > 1 else "",
            text2_ru=ru_parts[2] if len(ru_parts) > 2 else ""
        )

        total_generated += 1

    return total_generated


# --- yordamchi funksiyalar ---
def extract_bilingual(text: str):
    """Matndan 🇺🇿 va 🇷🇺 qismlarini ajratib olish."""
    uz, ru = "", ""
    for line in text.splitlines():
        if line.startswith("🇺🇿"):
            uz = line.replace("🇺🇿 Uzbekcha:", "").strip()
        elif line.startswith("🇷🇺"):
            ru = line.replace("🇷🇺 Русский:", "").strip()
    return uz or text, ru or text


def split_uz_ru(content: str):
    """2 blok (🇺🇿 va 🇷🇺) bo‘lib ajratish."""
    if "🇷🇺" in content:
        parts = content.split("🇷🇺", 1)
        uz = parts[0].replace("🇺🇿", "").strip()
        ru = "🇷🇺" + parts[1].strip()
        return uz, ru
    return content, content


def extract_question_line(content: str) -> str:
    """Matndan faqat 'Savol:' yoki 'Вопрос:' qatorini ajratib olish."""
    for line in content.splitlines():
        if line.lower().startswith(("savol", "вопрос")):
            return line.split(":", 1)[-1].strip()
    return content.strip()


def add_choice_variants(gen_q, content: str, lang="uz"):
    """Matndan variantlarni ajratib, bazaga yozadi."""
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    correct_letter = None

    for line in lines:
        if line.startswith(("A)", "B)", "C)", "D)")):
            letter, text = line.split(")", 1)
            kwargs = {
                "generated_question": gen_q,
                "letter": letter.strip(),
                "is_correct": False,
            }
            if lang == "uz":
                kwargs["text_uz"] = text.strip()
            else:
                kwargs["text_ru"] = text.strip()
            GeneratedChoiceOpenAi.objects.create(**kwargs)

        elif "to‘g‘ri javob" in line.lower() or "правильный" in line.lower():
            correct_letter = line.split(":")[-1].strip()

    if correct_letter:
        gen_q.generated_choices.filter(letter__iexact=correct_letter).update(is_correct=True)
