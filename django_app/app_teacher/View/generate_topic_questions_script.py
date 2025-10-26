from openai import OpenAI
from django_app.app_teacher.models import Topic, GeneratedQuestionOpenAi
from pdfminer.high_level import extract_text
import os, re

client = OpenAI(api_key=os.getenv("OPENAI"))

BOOK_PATH = os.path.join(os.path.dirname(__file__), "/home/user/backend/iq_math_orginal/Books/algebra-7.pdf")

def generate_topic_questions(subject_id: int, chapter_id: int, topic_id: int):
    topic = Topic.objects.select_related("chapter", "chapter__subject").get(id=topic_id)
    subject = topic.chapter.subject
    topic_name = topic.name_uz.strip()
    chapter_name = topic.chapter.name_uz.strip()
    total_generated = 0

    # 🔹 1️⃣ PDF dan matnni o‘qib olish
    try:
        full_text = extract_text(BOOK_PATH)
    except Exception as e:
        raise Exception(f"PDF o‘qishda xatolik: {e}")

    # 🔹 2️⃣ Mavzuni topamiz
    pattern = re.escape(topic_name)
    match = re.search(pattern, full_text, re.IGNORECASE)

    if not match:
        raise Exception(f"'{topic_name}' mavzusi PDF ichidan topilmadi.")

    start_index = match.start()

    # 🔹 3️⃣ Keyingi bobgacha bo‘lgan matnni ajratamiz
    rest_text = full_text[start_index:]
    next_chapter = re.search(r"\n\s*[A-ZА-ЯЁ0-9]+\..+\n", rest_text)
    end_index = next_chapter.start() if next_chapter else len(rest_text)
    topic_text = rest_text[:end_index].strip()

    # --- AI prompt yaratamiz
    for i in range(5):
        prompt = f"""
        Quyidagi darslik matniga asoslanib 7-sinf o‘quvchilari uchun matematika/algebra misollarini yarat:
        Fan: {subject.name_uz}
        Bob: {chapter_name}
        Mavzu: {topic_name}

        Darslikdan olingan matn:
        \"\"\"{topic_text[:2500]}\"\"\"  # faqat 2500 belgigacha

        Talablar:
        - Savol turi: text (matnli javob)
        - Misollar shu matndagi qoidalar yoki formulalarga mos bo‘lsin.
        - Murakkablik 7-sinf darajasiga mos (kasrlar, qavslar, o‘nli sonlar).
        - Har bir savol uchun to‘liq javobni yoz.
        - Format quyidagicha bo‘lsin:

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
            correct_answer_ru=ru_a,
        )
        total_generated += 1

    return total_generated


# --- yordamchi funksiyalar ---
def extract_bilingual_question_answer(text: str):
    uz_q = uz_a = ru_q = ru_a = ""
    current_lang = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if "🇺🇿" in line:
            current_lang = "uz"
        elif "🇷🇺" in line:
            current_lang = "ru"
        elif line.lower().startswith("savol:") and current_lang == "uz":
            uz_q = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("javob:") and current_lang == "uz":
            uz_a = line.split(":", 1)[-1].strip()
        elif line.lower().startswith("вопрос") and current_lang == "ru":
            ru_q = line.split(":", 1)[-1].strip()
        elif line.lower().startswith(("ответ", "ответ:")) and current_lang == "ru":
            ru_a = line.split(":", 1)[-1].strip()

    if not uz_q:
        uz_q = text.split("\n")[0][:200]
    if not ru_q:
        ru_q = uz_q
    return uz_q, uz_a, ru_q, ru_a
