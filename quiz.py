# quiz.py
import os
import django
import pandas as pd

# Django settings.py faylingizga yo'lni belgilang
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django_app.app_teacher.models import Question, Topic  # o'zingizning app nomingizni yozing

from ckeditor.fields import RichTextField

def import_questions_from_excel(file_path):
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        topic_name = row['topic_name_uz']
        topic = Topic.objects.filter(name_uz=topic_name).first()
        if not topic:
            print(f"Topic '{topic_name}' topilmadi. O'tkazib yuborildi.")
            continue

        question = Question(
            topic=topic,
            question_type='text',
            level=row['level'],

            # Multilingual maydonlar
            question_text_uz=row['question_text_uz'],
            question_text_ru=row['question_text_ru'],
            correct_text_answer_uz=row['answer_text_uz'],
            correct_text_answer_ru=row['answer_text_ru'],
        )
        question.save()
        print(f"Savol yaratildi: {question.question_text_uz[:50]}...")

if __name__ == '__main__':
    file_path = 'misollar.xlsx'  # Excel faylingizning nomi va joylashuvi
    import_questions_from_excel(file_path)
