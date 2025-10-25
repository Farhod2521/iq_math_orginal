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

    # ✅ 1️⃣ TEXT SAVOLLAR (UZ + RU)
    for i in range(5):
        prompt_uz = f"""
        Sen {subject.name} fanidan o‘quv test generatorisan.
        Mavzu: "{topic_name}"
        - Savol turi: text (matnli javob)
        - Foydalanuvchidan aniq javob kutiladi (raqam, so‘z yoki formula)
        - Savol aniq, qisqa va mantiqiy bo‘lsin.
        Natijani faqat savol matni ko‘rinishida qaytar.
        """
        prompt_ru = f"""
        Ты генератор учебных тестов по предмету {subject.name}.
        Тема: "{topic_name}"
        - Тип вопроса: текстовый ответ
        - Ожидается точный ответ (число, слово или формула)
        - Вопрос должен быть коротким и логическим.
        Верни только сам вопрос.
        """

        uz = client.responses.create(model="gpt-4o-mini", input=prompt_uz).output[0].content[0].text.strip()
        ru = client.responses.create(model="gpt-4o-mini", input=prompt_ru).output[0].content[0].text.strip()

        GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="text",
            generated_text_uz=uz,
            generated_text_ru=ru
        )
        total_generated += 1

    # ✅ 2️⃣ CHOICE SAVOLLAR (UZ + RU)
    for i in range(5):
        prompt_uz = f"""
        Sen {subject.name} fanidan test tuzuvchi AI assistantisan.
        Mavzu: "{topic_name}"
        Quyidagi formatda yangi test savolini yarat:
        Savol: (1 ta to‘g‘ri javobi bo‘lsin)
        A) ...
        B) ...
        C) ...
        D) ...
        To‘g‘ri javob: (A, B, C yoki D dan biri)
        """
        prompt_ru = f"""
        Ты AI ассистент, создающий тесты по предмету {subject.name}.
        Тема: "{topic_name}"
        Создай новый вопрос в формате:
        Вопрос:
        A) ...
        B) ...
        C) ...
        D) ...
        Правильный ответ: (A, B, C или D)
        """

        uz_content = client.responses.create(model="gpt-4o-mini", input=prompt_uz).output[0].content[0].text.strip()
        ru_content = client.responses.create(model="gpt-4o-mini", input=prompt_ru).output[0].content[0].text.strip()

        gen_q = GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="choice",
            generated_text_uz=extract_question_line(uz_content),
            generated_text_ru=extract_question_line(ru_content)
        )

        # UZ variantlar
        add_choice_variants(gen_q, uz_content, lang="uz")
        # RU variantlar
        add_choice_variants(gen_q, ru_content, lang="ru")

        total_generated += 1

    # ✅ 3️⃣ COMPOSITE SAVOLLAR (UZ + RU)
    for i in range(5):
        prompt_uz = f"""
        Sen {subject.name} fanidan o‘quv mashq generatorisan.
        Mavzu: "{topic_name}"
        Quyidagi formatda 1 ta kichik misol yarat:
        text1, correct_answer, text2
        Masalan: 12 + 5 = ___
        """
        prompt_ru = f"""
        Ты генератор учебных упражнений по предмету {subject.name}.
        Тема: "{topic_name}"
        Создай 1 пример в формате:
        text1, correct_answer, text2
        Например: 12 + 5 = ___
        """

        uz_content = client.responses.create(model="gpt-4o-mini", input=prompt_uz).output[0].content[0].text.strip()
        ru_content = client.responses.create(model="gpt-4o-mini", input=prompt_ru).output[0].content[0].text.strip()

        uz_parts = [p.strip() for p in uz_content.split(",")]
        ru_parts = [p.strip() for p in ru_content.split(",")]

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
