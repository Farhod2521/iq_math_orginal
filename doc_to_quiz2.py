import os
import django
from docx import Document
from django.core.files.base import ContentFile
import uuid
import re
from bs4 import BeautifulSoup

# Django muhitini yuklash
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from django_app.app_teacher.models import Question, Topic


def convert_math_fractions(text):
    """
    Word'dagi oddiy kasr formatlarini HTML/RichText formatiga o'girish
    Masalan: 1/2 → <span class="math-fraction">1/2</span>
    """
    # Oddiy kasrlar uchun regex
    pattern = r'(\d+)/(\d+)'
    replacement = r'<span class="math-fraction">\1/\2</span>'
    return re.sub(pattern, replacement, text)

def process_docx_paragraphs(doc):
    """
    Word hujjatidagi paragraflarni qayta ishlash va HTML formatiga o'tkazish
    """
    html_content = ""
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            # Kasrlarni konvert qilish
            text = convert_math_fractions(text)
            # Style'larni saqlab qolish
            if para.style.name.startswith('Heading'):
                level = int(para.style.name[-1])
                html_content += f"<h{level}>{text}</h{level}>"
            else:
                html_content += f"<p>{text}</p>"
    return html_content

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

    # Word hujjatidagi barcha rasmlarni yig'amiz
    image_parts = [
        rel.target_part.blob
        for rel in doc.part._rels.values()
        if "image" in rel.target_ref
    ]

    image_index = 0

    for row in doc.tables[0].rows[1:]:
        cells = row.cells
        if len(cells) < 5:
            continue  # noto'g'ri satr

        try:
            level = int(cells[0].text.strip())
        except ValueError:
            level = 1

        # Matnlarni qayta ishlash
        uz_question = process_docx_paragraphs(cells[1])
        uz_answer = convert_math_fractions(cells[2].text.strip())
        ru_question = process_docx_paragraphs(cells[3])
        ru_answer = convert_math_fractions(cells[4].text.strip())

        # Rasmni biriktirish (agar mavjud bo'lsa)
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
            question_text=f"{uz_question}{image_html}",
            question_text_ru=ru_question
        )

    print("✅ Import tugadi.")

# Foydalanish:
if __name__ == "__main__":
    import_docx_questions("/path/to/your/document.docx", "Kasrlarni bo'lish")