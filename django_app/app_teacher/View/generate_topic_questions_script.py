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
    chapter = topic.chapter

    total_generated = 0
    topic_name = topic.name

    # --- 1️⃣ TEXT SAVOLLAR (5 ta) ---
    for i in range(5):
        prompt = f"""
        Sen {subject.name} fanidan o‘quv test generatorisan.
        Mavzu: "{topic_name}"
        Quyidagi talab bo‘yicha yangi savol yarat:
        - Savol turi: text (matnli javob)
        - Foydalanuvchidan aniq javob kutiladi (raqam, so‘z yoki formula)
        - Savol aniq, qisqa va o‘quvchining mantiqiy fikrlashini sinasin.
        Natijani faqat savol matni ko‘rinishida qaytar.
        """
        response = client.responses.create(model="gpt-4o-mini", input=prompt)
        q_text = response.output[0].content[0].text.strip()

        GeneratedQuestionOpenAi.objects.create(
            base_question=None,
            topic=topic,
            generated_text=q_text,
            correct_answer=None
        )
        total_generated += 1

    # --- 2️⃣ CHOICE SAVOLLAR (5 ta) ---
    for i in range(5):
        prompt = f"""
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
        response = client.responses.create(model="gpt-4o-mini", input=prompt)
        content = response.output[0].content[0].text.strip()

        # Matndan ajratib olish
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        gen_q = GeneratedQuestionOpenAi.objects.create(
            base_question=None,
            topic=topic,
            generated_text=lines[0].replace("Savol:", "").strip()
        )

        correct_letter = None
        for line in lines[1:]:
            if line.startswith(("A)", "B)", "C)", "D)")):
                letter, text = line.split(")", 1)
                GeneratedChoiceOpenAi.objects.create(
                    generated_question=gen_q,
                    letter=letter.strip(),
                    text=text.strip(),
                    is_correct=False
                )
            elif "To‘g‘ri javob" in line or "Javob" in line:
                correct_letter = line.split(":")[-1].strip()

        if correct_letter:
            gen_q.generated_choices.filter(letter__iexact=correct_letter).update(is_correct=True)
        total_generated += 1

    # --- 3️⃣ COMPOSITE SAVOLLAR (5 ta) ---
    for i in range(5):
        prompt = f"""
        Sen {subject.name} fanidan o‘quv mashq generatorisan.
        Mavzu: "{topic_name}"
        1 ta kichik bo‘limli misol yarat:
        Masalan: 12 + 5 = ___
        Yoki: ... + ... = ...
        Format:
        text1, correct_answer, text2
        """
        response = client.responses.create(model="gpt-4o-mini", input=prompt)
        content = response.output[0].content[0].text.strip()

        parts = [p.strip() for p in content.split(",")]
        text1 = parts[0] if len(parts) > 0 else ""
        correct = parts[1] if len(parts) > 1 else ""
        text2 = parts[2] if len(parts) > 2 else ""

        gen_q = GeneratedQuestionOpenAi.objects.create(
            base_question=None,
            topic=topic,
            generated_text=f"{topic_name} uchun mashq"
        )

        GeneratedSubQuestionOpenAi.objects.create(
            generated_question=gen_q,
            text1=text1,
            correct_answer=correct,
            text2=text2
        )
        total_generated += 1

    return total_generated
