import os
import django
import zipfile
import uuid
import xml.etree.ElementTree as ET
from docx import Document
from django.core.files.base import ContentFile

# Django muhitini yuklash
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from django_app.app_teacher.models import Question, Topic


# MathML formulani oddiy textga aylantirish (basic versiya)
def extract_equations_from_docx(docx_path):
    zipf = zipfile.ZipFile(docx_path)
    equations = []

    for name in zipf.namelist():
        if name.startswith("word/document") and name.endswith(".xml"):
            xml_content = zipf.read(name)
            root = ET.fromstring(xml_content)

            # OMML namespace
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
            }

            for omath in root.findall(".//m:oMath", namespaces):
                text_parts = []
                for t in omath.findall(".//m:t", namespaces):
                    text_parts.append(t.text)
                if text_parts:
                    equations.append("".join(text_parts))
    return equations


def import_docx_questions(docx_path, topic_name):
    doc = Document(docx_path)
    formulas = extract_equations_from_docx(docx_path)

    try:
        topic = Topic.objects.get(name=topic_name)
    except Topic.DoesNotExist:
        print(f"Topic '{topic_name}' topilmadi.")
        return

    chapter = topic.chapter
    if not chapter:
        print(f"Topic '{topic_name}' uchun chapter mavjud emas.")
        return

    image_parts = [
        rel.target_part.blob
        for rel in doc.part._rels.values()
        if "image" in rel.target_ref
    ]

    image_index = 0
    formula_index = 0

    for row in doc.tables[0].rows[1:]:
        cells = row.cells
        if len(cells) < 5:
            continue

        try:
            level = int(cells[0].text.strip())
        except ValueError:
            level = 1

        uz_question_raw = cells[1].text.strip()
        uz_answer = cells[2].text.strip()
        ru_question_raw = cells[3].text.strip()
        ru_answer = cells[4].text.strip()

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

        # Agar formula mavjud bo‘lsa, uni qo‘shamiz
        if formula_index < len(formulas):
            uz_question += f"<br><b>Formula:</b> {formulas[formula_index]}"
            formula_index += 1

        # Rasmni biriktirish
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

        # Bazaga saqlash
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
