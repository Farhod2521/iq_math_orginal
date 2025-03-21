import os
from docx import Document
from django.core.management.base import BaseCommand
from django_app.app_teacher.models import Question, Topic
from PIL import Image

class Command(BaseCommand):
    help = "Word fayldan savollarni yuklash (rasmlar bilan)"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Word fayl yo'li")
        parser.add_argument("--image_dir", type=str, default="question_images", help="Rasmlarni saqlash uchun papka")

    def handle(self, *args, **options):
        file_path = options["file_path"]
        image_dir = options["image_dir"]

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        doc = Document(file_path)
        question_data = []
        current_question = {}
        image_counter = 0

        for para in doc.paragraphs:
            text = para.text.strip()

            # Rasmlarni o'qish va saqlash
            for run in para.runs:
                if run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}blip"):
                    image = run._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}blip")[0]
                    image_rid = image.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"]
                    image_data = doc.part.rels[image_rid].target_part.blob
                    image_filename = f"image_{image_counter}.png"
                    image_path = os.path.join(image_dir, image_filename)

                    try:
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                    except IOError as e:
                        self.stdout.write(self.style.ERROR(f"❌ Rasmni saqlashda xatolik: {e}"))
                        continue

                    text += f'<br><img src="{os.path.join(image_dir, image_filename)}" style="max-width:100%;"><br>'
                    image_counter += 1

            if text.startswith("topic_id="):
                if current_question:
                    question_data.append(current_question)

                topic_id = int(text.replace("topic_id=", "").strip())
                try:
                    topic = Topic.objects.get(id=topic_id)
                except Topic.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"❌ Topic ID {topic_id} topilmadi!"))
                    continue

                current_question = {
                    "topic": topic,
                    "question_text_uz": "",
                    "question_text_ru": "",
                    "correct_answer_uz": "",
                    "correct_answer_ru": "",
                    "level": 1
                }

            elif text.startswith("question_text_uz:"):
                current_question["question_text_uz"] = text.replace("question_text_uz:", "").strip()

            elif text.startswith("question_text_ru:"):
                current_question["question_text_ru"] = text.replace("question_text_ru:", "").strip()

            elif text.startswith("correct_answer_uz:"):
                current_question["correct_answer_uz"] = text.replace("correct_answer_uz:", "").strip()

            elif text.startswith("correct_answer_ru:"):
                current_question["correct_answer_ru"] = text.replace("correct_answer_ru:", "").strip()

            elif text.startswith("level :"):
                current_question["level"] = int(text.replace("level :", "").strip())

        if current_question:
            question_data.append(current_question)

        for q in question_data:
            Question.objects.create(
                topic=q["topic"],
                question_text_uz=q["question_text_uz"],
                question_text_ru=q["question_text_ru"],
                correct_answer_uz=q["correct_answer_uz"],
                correct_answer_ru=q["correct_answer_ru"],
                level=q["level"]
            )

        self.stdout.write(self.style.SUCCESS(f"✅ {len(question_data)} ta savol bazaga yuklandi!"))