from openai import OpenAI
from django_app.app_teacher.models import  Topic, Question, GeneratedQuestionOpenAi, GeneratedChoiceOpenAi, GeneratedSubQuestionOpenAi
import os
client = OpenAI(api_key=f"{os.getenv('OPENAI')}")

def generate_topic_questions(topic_id: int):
    topic = Topic.objects.get(id=topic_id)
    questions = topic.questions.all()
    total_generated = 0

    for q in questions:
        if q.question_type == "text":
            _generate_text_question(q, topic)
        elif q.question_type in ["choice", "image_choice"]:
            _generate_choice_question(q, topic)
        elif q.question_type == "composite":
            _generate_composite_question(q, topic)
        total_generated += 1

    return total_generated


def _generate_text_question(q, topic):
    prompt = f"""
    Quyidagi savolga o‘xshash, lekin raqam yoki qiymatlarni o‘zgartirib yangi matematik misol yarat:
    Savol: {q.question_text}
    Faqat yangi misolni qaytar, izohsiz.
    """
    response = client.responses.create(model="gpt-4o-mini", input=prompt)
    new_text = response.output[0].content[0].text.strip()

    GeneratedQuestionOpenAi.objects.create(
        base_question=q,
        topic=topic,
        generated_text=new_text,
        correct_answer=None,
    )


def _generate_choice_question(q, topic):
    # 1️⃣ Savolni generatsiya qilish
    prompt_q = f"""
    Ushbu test savoliga o‘xshash yangi savol yoz, faqat raqam yoki faktlar biroz boshqacha bo‘lsin:
    Savol: {q.question_text}
    """
    question_res = client.responses.create(model="gpt-4o-mini", input=prompt_q)
    new_q_text = question_res.output[0].content[0].text.strip()

    # 2️⃣ Variantlarni generatsiya qilish
    prompt_choices = f"""
    Quyidagi savol uchun 4 ta variant yarat (A, B, C, D).
    Faqat bittasi to‘g‘ri bo‘lsin. Formati:
    A) ...
    B) ...
    C) ...
    D) ...
    To‘g‘ri javob: ...
    Savol: {new_q_text}
    """
    choice_res = client.responses.create(model="gpt-4o-mini", input=prompt_choices)
    choice_text = choice_res.output[0].content[0].text.strip()

    # Variantlarni ajratish
    lines = [l.strip() for l in choice_text.split("\n") if l.strip()]
    gen_q = GeneratedQuestionOpenAi.objects.create(base_question=q, topic=topic, generated_text=new_q_text)

    correct_letter = None
    for l in lines:
        if l.startswith(("A)", "B)", "C)", "D)")):
            letter, text = l.split(")", 1)
            GeneratedChoice.objects.create(
                generated_question=gen_q,
                letter=letter.strip(),
                text=text.strip(),
                is_correct=False
            )
        elif "To‘g‘ri javob" in l or "Javob" in l:
            correct_letter = l.split(":")[-1].strip()

    # ✅ To‘g‘ri javobni belgilang
    if correct_letter:
        gen_q.generated_choices.filter(letter__iexact=correct_letter).update(is_correct=True)


def _generate_composite_question(q, topic):
    for sub in q.sub_questions.all():
        prompt = f"""
        Quyidagi kichik savolni o‘xshash tarzda, faqat raqamlarni o‘zgartirib yoz:
        {sub.text1 or ''} ___ {sub.text2 or ''}
        To‘g‘ri javob: {sub.correct_answer}
        """
        res = client.responses.create(model="gpt-4o-mini", input=prompt)
        new_text = res.output[0].content[0].text.strip()

        # Yangi asosiy savol yaratish (agar hali bo‘lmasa)
        gen_q = GeneratedQuestionOpenAi.objects.create(
            base_question=q,
            topic=topic,
            generated_text=f"{q.question_text[:100]}..."
        )

        GeneratedSubQuestion.objects.create(
            generated_question=gen_q,
            text1=new_text,
            correct_answer=None,
            text2=""
        )
