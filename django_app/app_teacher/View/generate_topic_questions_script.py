from openai import OpenAI
from django_app.app_teacher.models import Topic, GeneratedQuestionOpenAi
from pdfminer.high_level import extract_text
import os, re, random

client = OpenAI(api_key=os.getenv("OPENAI"))

BOOK_PATH = "/home/user/backend/iq_math_orginal/Books/algebra-7.pdf"


def generate_topic_questions(subject_id: int, chapter_id: int, topic_id: int):
    topic = Topic.objects.select_related("chapter", "chapter__subject").get(id=topic_id)
    subject = topic.chapter.subject
    topic_name = topic.name_uz.strip()
    chapter_name = topic.chapter.name_uz.strip()
    total_generated = 0

    # 1️⃣ PDF matnini o‘qib olish
    try:
        full_text = extract_text(BOOK_PATH)
    except Exception as e:
        raise Exception(f"PDF o‘qishda xatolik: {e}")

    # 2️⃣ Mavzuni aniq sarlavha sifatida topish
    # sarlavha aynan shu nomda bo‘lishi kerak (katta harflarda bo‘lishi mumkin)
    topic_pattern = re.compile(rf"(?i)\b{re.escape(topic_name)}\b")
    match = topic_pattern.search(full_text)
    if not match:
        raise Exception(f"'{topic_name}' mavzusi PDF ichidan topilmadi.")

    start_index = match.start()
    rest_text = full_text[start_index:]

    # 3️⃣ “Mashqlar” so‘zini topamiz
    mashqlar_match = re.search(r"(?i)Mashqlar", rest_text)
    if not mashqlar_match:
        raise Exception("Mashqlar bo‘limi topilmadi.")

    mashq_text = rest_text[mashqlar_match.end():]

    # 4️⃣ Mashqlarni raqamlar bo‘yicha ajratish (1), 2), 3)...)
    mashqlar = re.split(r"\n\s*\d+\)\s*", mashq_text)
    mashqlar = [m.strip() for m in mashqlar if len(m.strip()) > 20][:10]  # 10 tadan oshmasin

    if not mashqlar:
        raise Exception("Mashqlar topilmadi yoki juda qisqa.")

    # 5️⃣ Har bir mashqdan bitta misol tanlash
    random.shuffle(mashqlar)
    selected_tasks = mashqlar[:5]

    for i, mashq in enumerate(selected_tasks, start=1):
        prompt = f"""
        Quyidagi 7-sinf algebra darsligidagi mashqni o‘qib, uni yechib natijani yoz:
        Fan: {subject.name_uz}
        Bob: {chapter_name}
        Mavzu: {topic_name}

        Mashq:
        \"\"\"{mashq[:1000]}\"\"\"

        Talab:
        - Faqat bitta savolni yech.
        - Javobni aniq yoz (raqam yoki ifoda).
        - Format quyidagicha bo‘lsin:
        🇺🇿 Uzbekcha:
        Savol: ...
        Javob: ...
        🇷🇺 Русский:
        Вопрос: ...
        Ответ: ...
        """

        try:
            res = client.responses.create(model="gpt-4o-mini", input=prompt)
            text = res.output[0].content[0].text.strip()
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


# --- yordamchi funksiya ---
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
