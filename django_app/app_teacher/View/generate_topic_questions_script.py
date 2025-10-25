from openai import OpenAI
from django_app.app_teacher.models import Topic, GeneratedQuestionOpenAi
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
        Sen {subject.classes.name}-sinf {subject.name} fanidan o‘quv test generatorisan.
        Bob: {chapter_name}
        Mavzu: "{topic_name}"
        - Savol turi: text (matnli javob)
        - Foydalanuvchidan aniq javob kutiladi (raqam, so‘z yoki formula)
        - Savol aniq va mantiqiy bo‘lsin.
        Natijani quyidagi formatda qaytar:

        🇺🇿 Uzbekcha:
        Savol: ...
        Javob: ...
        🇷🇺 Русский:
        Вопрос: ...
        Ответ: ...
        """

        try:
            response = client.responses.create(model="gpt-4o-mini", input=prompt)
            text = response.output[0].content[0].text.strip()
        except Exception as e:
            print(f"⚠️ OpenAI xatolik: {e}")
            continue

        uz_q, uz_a, ru_q, ru_a = extract_bilingual_question_answer(text)

        GeneratedQuestionOpenAi.objects.create(
            topic=topic,
            question_type="text",
            generated_text_uz=uz_q,
            correct_answer_uz=uz_a,
            generated_text_ru=ru_q,
            correct_answer_ru=ru_a
        )
        total_generated += 1

    return total_generated


# --- yordamchi funksiyalar ---
def extract_bilingual_question_answer(text: str):
    """Matndan 🇺🇿 va 🇷🇺 qismlarini, shuningdek Savol/Javob bo‘limlarini ajratib olish."""
    uz_q = uz_a = ru_q = ru_a = ""
    current_lang = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("🇺🇿"):
            current_lang = "uz"
        elif line.startswith("🇷🇺"):
            current_lang = "ru"
        elif line.lower().startswith("savol:") and current_lang == "uz":
            uz_q = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("javob:") and current_lang == "uz":
            uz_a = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("вопрос") and current_lang == "ru":
            ru_q = line.split(":", 1)[-1].strip()
        elif line.lower().startswith(("ответ", "ответ:")) and current_lang == "ru":
            ru_a = line.split(":", 1)[-1].strip()

    # Agar AI formatni biroz o‘zgartirsa, fallback sifatida birinchi satrlarni olib qo‘yamiz
    if not uz_q:
        uz_q = text.split("\n")[0][:200]
    if not ru_q:
        ru_q = uz_q
    return uz_q, uz_a, ru_q, ru_a