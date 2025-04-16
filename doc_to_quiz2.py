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

    # Word hujjatidagi barcha rasmlarni yig‘amiz
    image_parts = [
        rel.target_part.blob
        for rel in doc.part._rels.values()
        if "image" in rel.target_ref
    ]

    image_index = 0

    for row in doc.tables[0].rows[1:]:
        cells = row.cells
        if len(cells) < 5:
            continue  # noto‘liq satr bo‘lsa

        try:
            level = int(cells[0].text.strip())
        except ValueError:
            level = 1

        uz_question_raw = cells[1].text.strip()
        uz_answer = cells[2].text.strip()
        ru_question_raw = cells[3].text.strip()
        ru_answer = cells[4].text.strip()

        # Ajratilgan holatda – ikkita til ketma-ket yozilgan bo‘lsa
        def split_text(text):
            lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
            if len(lines) >= 2:
                return lines[0], " ".join(lines[1:])
            elif len(lines) == 1:
                return lines[0], ""
            else:
                return "", ""

        uz_question, uz_extra = split_text(uz_question_raw)
        ru_question, ru_extra = split_text(ru_question_raw)

        if uz_extra:
            uz_question += " " + uz_extra
        if ru_extra:
            ru_question += " " + ru_extra

        # Rasmni biriktirish (agar mavjud bo‘lsa)
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

        # Question yaratish
        Question.objects.create(
            topic=topic,
            question_type="text",
            level=level,
            correct_text_answer=uz_answer,
            question_text_uz=f"{uz_question}{image_html}",
            question_text_ru=ru_question
        )

    print("✅ Import tugadi.")

# Foydalanish:
if __name__ == "__main__":
    import_docx_questions("/home/user/backend/iq_math_orginal/testdoc/5.docx", "Kasrlarni bo‘lish")
