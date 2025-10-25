from openai import OpenAI
from django_app.app_teacher.models import (
    Topic,
    GeneratedQuestionOpenAi
)
import os

client = OpenAI(api_key=os.getenv("OPENAI"))


def generate_topic_questions(subject_id: int, chapter_id: int, topic_id: int):
    topic = Topic.objects.select_related("chapter", "chapter__subject").get(id=topic_id)
    subject = topic.chapter.subject
    topic_name = topic.name
    chapter_name = topic.chapter.name
    total_generated = 0

    # ✅ 1️⃣ FAQAT TEXT SAVOLLAR (5 ta, UZ + RU)
    for i in range(5):
        prompt = f"""
        Sen {subject.classes.name}-{subject.name} fanidan o‘quv savol generatsiya qilib ber.
        BOB:{chapter_name}   Mavzu: "{topic_name}"
        - Savol turi: text (matnli javob)
        - Foydalanuvchidan aniq javob kutiladi (raqam, so‘z yoki formula)
        - Savol aniq, va mantiqiy bo‘lsin.
        Natijani quyidagi formatda 2 tilda qaytar:
        🇺🇿 Uzbekcha: ...
        🇷🇺 Русский: ...
        """

        try:
            response = client.responses.create(model="gpt-4o-mini", input=prompt)
            text = response.output[0].content[0].text.strip()
        except Exception as e:
            print(f"⚠️ OpenAI xatolik: {e}")
            continue

        # Matndan ikkita tilni ajratamiz
        uz_text, ru_text = extract_bilingual(text)

        GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="text",
            generated_text_uz=uz_text,
            generated_text_ru=ru_text
        )
        total_generated += 1

    # 🔒 Quyidagilar hozircha o‘chirib turilgan (keyin faollashtiramiz)
    """
    # ✅ 2️⃣ CHOICE SAVOLLAR (3 ta)
    for i in range(3):
        ...
    
    # ✅ 3️⃣ COMPOSITE SAVOLLAR (2 ta)
        ...
    """

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
