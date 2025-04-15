import os
import django
from docx import Document
from django.core.files.base import ContentFile
import uuid

# Django muhitini yuklash
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

# Django modellari
from django_app.app_teacher.models import Question, Topic, Chapter  # Chapter ham kerak

def import_docx_questions(docx_path, topic_name):
    doc = Document(docx_path)
    try:
        topic = Topic.objects.get(name=topic_name)
    except Topic.DoesNotExist:
        print(f"Topic '{topic_name}' topilmadi.")
        return

    chapter = topic.chapter
    if not chapter:
        print(f"Topic '{topic_name}' uchun chapter mavjud emas.")
        return

    # Word faylidagi barcha rasmlarni to‘plash
    image_parts = [
        rel.target_part.blob
        for rel in doc.part._rels.values()
        if "image" in rel.target_ref
    ]

    image_index = 0

    for row in doc.tables[0].rows[1:]:
        uz_question = row.cells[1].text.strip()
        uz_answer = row.cells[2].text.strip()
        ru_question = row.cells[3].text.strip()
        ru_answer = row.cells[4].text.strip()

        image_html = ""
        # Har bir satrga rasm biriktirish (agar mavjud bo‘lsa)
        if image_index < len(image_parts):
            img_data = image_parts[image_index]
            image_name = f"{uuid.uuid4()}.png"
            media_dir = "media/imported"
            os.makedirs(media_dir, exist_ok=True)
            image_path = os.path.join(media_dir, image_name)

            with open(image_path, "wb") as f:
                f.write(img_data)

            image_html = f'<img src="/media/imported/{image_name}" alt="Image">'
            image_index += 1

        # Savolni yaratish
        Question.objects.create(
            topic=topic,
            question_type="text",
            level=1,
            correct_text_answer=uz_answer,
            question_text=f"<p>{uz_question}</p>{image_html}",
        )

# Foydalanish:
if __name__ == "__main__":
    import_docx_questions("/home/user/backend/iq_math_orginal/testdoc/5.docx", "Termometrlar")
