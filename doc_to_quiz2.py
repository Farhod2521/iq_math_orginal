import os
import django
from docx import Document
from django.core.files.base import ContentFile
import uuid

# Django muhitini yuklash
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from django_app.app_teacher.models import Question, Topic


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

    # Word hujjatidagi barcha rasmlarni yig‘ib olamiz
    image_parts = [
        rel.target_part.blob
        for rel in doc.part._rels.values()
        if "image" in rel.target_ref
    ]

    image_index = 0

    for row in doc.tables[0].rows[1:]:
        cells = row.cells
        if len(cells) < 5:
            continue  # noto‘liq satr bo‘lsa, o‘tkazib yuboramiz

        try:
            level = int(cells[0].text.strip())
        except ValueError:
            level = 1  # default qiymat

        uz_question = cells[1].text.strip()
        uz_answer = cells[2].text.strip()
        ru_question = cells[3].text.strip()
        ru_answer = cells[4].text.strip()

        # Rasmni yuklash
        image_html = ""
        if image_index < len(image_parts):
            img_data = image_parts[image_index]
            image_name = f"{uuid.uuid4()}.png"
            media_dir = "media/imported"
            os.makedirs(media_dir, exist_ok=True)
            image_path = os.path.join(media_dir, image_name)

            with open(image_path, "wb") as f:
                f.write(img_data)

            image_html = f'<br><img src="/media/imported/{image_name}" alt="Image">'
            image_index += 1

        # Savolni HTML formatda saqlash (o‘zbek va rus tilidagi matnlar)
        full_question = f"<p><b>UZ:</b> {uz_question}</p><p><b>RU:</b> {ru_question}</p>{image_html}"

        # To‘g‘ri javob faqat o‘zbekcha yoziladi
        Question.objects.create(
            topic=topic,
            question_type="text",
            level=level,
            correct_text_answer=uz_answer,
            question_text=full_question,
        )

    print("Import tugadi.")

# Foydalanish:
if __name__ == "__main__":
    import_docx_questions("/home/user/backend/iq_math_orginal/testdoc/5.docx", "Kasrlarni bo‘lish")
