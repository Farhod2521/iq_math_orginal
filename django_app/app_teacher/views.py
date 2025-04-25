from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import  Chapter, Topic, Question
from .serializers import(
    SubjectSerializer, MyChapterAddSerializer, MyTopicAddSerializer,
    ChoiceSerializer, CompositeSubQuestionSerializer, QuestionSerializer, SubjectRegisterSerilzier
)
from django_app.app_user.models import  Subject
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView


class SubjectListAPIView(ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectRegisterSerilzier





class TeacherSubjectsAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Faqat tizimga kirgan foydalanuvchilar

    def get(self, request):
        teacher = request.user.teacher_profile  # Tizimga kirgan o‘qituvchini olish
        subjects = Subject.objects.filter(teachers=teacher)  # O‘qituvchiga bog‘langan fanlar
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)

    def put(self, request, pk):
        teacher = request.user.teacher_profile
        try:
            subject = Subject.objects.get(pk=pk, teachers=teacher)
        except Subject.DoesNotExist:
            return Response({"error": "Bu fan sizga tegishli emas yoki mavjud emas."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubjectSerializer(subject, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        teacher = request.user.teacher_profile
        try:
            subject = Subject.objects.get(pk=pk, teachers=teacher)
        except Subject.DoesNotExist:
            return Response({"error": "Bu fan sizga tegishli emas yoki mavjud emas."}, status=status.HTTP_404_NOT_FOUND)

        subject.delete()
        return Response({"message": "Fan o‘chirildi."}, status=status.HTTP_204_NO_CONTENT)
    
class MyChapterAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile
        subject_id = request.data.get("subject")

        if not subject_id:
            return Response({"error": "Fan ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(id=subject_id, teachers=teacher)
        except Subject.DoesNotExist:
            return Response({"error": "Siz bu fanga bo'lim qo'sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyChapterAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(subject=subject)  # yoki kerakli boshqa fieldlar
            return Response({"message": "Chapter yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTopicAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile
        chapter_id = request.data.get("chapter")

        if not chapter_id:
            return Response({"error": "Chapter ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chapter = Chapter.objects.get(id=chapter_id, subject__teachers=teacher)
        except Chapter.DoesNotExist:
            return Response({"error": "Siz bu bo‘limga mavzu qo‘sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyTopicAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(chapter=chapter)  # kerakli bo‘lsa `chapter`ni o‘zing kirit
            return Response({"message": "Topic yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    

class MyQuestionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        try:
            topic = Topic.objects.get(id=id)
        except Topic.DoesNotExist:
            return Response({"error": "Mavzu topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        
        questions = Question.objects.filter(topic=topic).prefetch_related('sub_questions', 'choices')
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class MyChapterListView(APIView):
    """Tizimga kirgan o‘qituvchining barcha bo‘limlarini olish"""
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        teacher = request.user.teacher_profile  
        subjects = Subject.objects.filter(teachers=teacher)  
        chapters = Chapter.objects.filter(subject__in=[id])  

        serializer = MyChapterAddSerializer(chapters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        chapter = get_object_or_404(Chapter, id=id)
        serializer = MyChapterAddSerializer(chapter, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        chapter = get_object_or_404(Chapter, id=id)
        chapter.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class MyTopicListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
    
        topics = Topic.objects.filter(chapter__in=[id])

        serializer = MyTopicAddSerializer(topics, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def put(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        serializer = MyTopicAddSerializer(topic, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        topic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


################################  QUESTION BY TEACHER CREATE ##################################################
from django.db import transaction
   
class QuestionAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = QuestionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    question = serializer.save()

                    # Choice savollarini saqlash
                    if question.question_type in ['choice', 'image_choice']:
                        choices_data = request.data.get('choices', [])
                        if not choices_data:
                            raise ValueError("Choice savollar uchun variantlar kiritilmagan")
                        
                        # Avvalgi choicelarni o'chirish
                        question.choices.all().delete()
                        
                        for idx, choice_data in enumerate(choices_data):
                            # Agar letter mavjud bo'lmasa, harflarni avtomatik belgilash
                            if 'letter' not in choice_data or not choice_data['letter']:
                                choice_data['letter'] = chr(65 + idx)  # 65 = 'A' ASCII kodi
                            
                            choice_data['question'] = question.id
                            choice_serializer = ChoiceSerializer(data=choice_data, context={'request': request})
                            if choice_serializer.is_valid():
                                choice = choice_serializer.save()
                                # Rasmni alohida saqlash
                                if 'image' in request.FILES:
                                    image_file = request.FILES.get(f'choices[{idx}].image')
                                    if image_file:
                                        choice.image = image_file
                                        choice.save()
                            else:
                                raise ValueError(f"Variantdagi ma'lumotlar noto‘g‘ri: {choice_serializer.errors}")

                    # Composite savollarini saqlash
                    elif question.question_type == 'composite':
                        sub_questions_data = request.data.get('sub_questions', [])
                        if not sub_questions_data:
                            raise ValueError("Composite savol uchun kichik savollar kiritilmagan")
                        
                        # Avvalgi sub_questionlarni o'chirish
                        question.sub_questions.all().delete()
                        
                        for sub_data in sub_questions_data:
                            sub_data['question'] = question.id
                            sub_serializer = CompositeSubQuestionSerializer(data=sub_data)
                            if sub_serializer.is_valid():
                                sub_serializer.save()
                            else:
                                raise ValueError(f"Kichik savoldagi ma'lumotlar noto‘g‘ri: {sub_serializer.errors}")

                return Response(QuestionSerializer(question, context={'request': request}).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
################################  QUESTION BY TEACHER DELETE ##################################################

class QuestionDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        question.delete()
        return Response({"message": "Savol muvaffaqiyatli o‘chirildi."}, status=status.HTTP_204_NO_CONTENT)

################################  QUESTION BY TEACHER UPDATE ##################################################

class QuestionUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        serializer = QuestionSerializer(question, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    question = serializer.save()

                    # Choice savollarini yangilash
                    if question.question_type in ['choice', 'image_choice']:
                        choices_data = request.data.get('choices', [])
                        if not choices_data:
                            raise ValueError("Choice savollar uchun variantlar kiritilmagan")

                        question.choices.all().delete()

                        for idx, choice_data in enumerate(choices_data):
                            if 'letter' not in choice_data or not choice_data['letter']:
                                choice_data['letter'] = chr(65 + idx)

                            choice_data['question'] = question.id
                            choice_serializer = ChoiceSerializer(data=choice_data, context={'request': request})
                            if choice_serializer.is_valid():
                                choice = choice_serializer.save()
                                image_file = request.FILES.get(f'choices[{idx}].image')
                                if image_file:
                                    choice.image = image_file
                                    choice.save()
                            else:
                                raise ValueError(f"Variantdagi ma'lumotlar noto‘g‘ri: {choice_serializer.errors}")

                    # Composite savollarini yangilash
                    elif question.question_type == 'composite':
                        sub_questions_data = request.data.get('sub_questions', [])
                        if not sub_questions_data:
                            raise ValueError("Composite savol uchun kichik savollar kiritilmagan")

                        question.sub_questions.all().delete()

                        for sub_data in sub_questions_data:
                            sub_data['question'] = question.id
                            sub_serializer = CompositeSubQuestionSerializer(data=sub_data)
                            if sub_serializer.is_valid():
                                sub_serializer.save()
                            else:
                                raise ValueError(f"Kichik savoldagi ma'lumotlar noto‘g‘ri: {sub_serializer.errors}")

                return Response(QuestionSerializer(question, context={'request': request}).data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from openpyxl import load_workbook
from io import BytesIO
from django.http import HttpResponse
import os
import pandas as pd
class QuestionToXlsxImport(APIView):
    def post(self, request):
        topic_id = request.data.get("topic_id")
        topic_name_uz = request.data.get("topic_name_uz")

        if not topic_id or not topic_name_uz:
            return Response({"error": "topic_id and topic_name_uz are required"}, status=status.HTTP_400_BAD_REQUEST)

        template_path = 'shablon.xlsx'
        if not os.path.exists(template_path):
            return Response({"error": "shablon.xlsx topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        workbook = load_workbook(template_path)
        sheet = workbook.active

        next_row = sheet.max_row + 1
        sheet.cell(row=next_row, column=1, value=topic_id)
        sheet.cell(row=next_row, column=2, value=topic_name_uz)

        # BytesIO bilan faylni virtual tarzda saqlash
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=shablon_yangilangan.xlsx'
        return response
    

class QuestionImportFromXlsx(APIView):
    def post(self, request):
        file = request.FILES.get('file')

        if not file:
            return Response({"error": "Fayl yuborilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(BytesIO(file.read()))
        except Exception as e:
            return Response({"error": f"Excel faylni o'qishda xatolik: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        skipped = []

        for index, row in df.iterrows():
            topic_id = row.get('topic_id')
            if not topic_id:
                skipped.append(f"{index + 2}-qator: topic_id yo'q")
                continue

            try:
                topic = Topic.objects.get(id=topic_id)
            except Topic.DoesNotExist:
                skipped.append(f"{index + 2}-qator: Topic ID {topic_id} topilmadi")
                continue

            question = Question.objects.create(
                topic=topic,
                question_type='text',  # Agar boshqa type bo‘lsa, excelga qo‘shib o‘zgartirish mumkin
                level=row.get('level') or 1,
                question_text_uz=row.get('question_text_uz', ''),
                question_text_ru=row.get('question_text_ru', ''),
                correct_text_answer_uz=row.get('answer_text_uz', ''),
                correct_text_answer_ru=row.get('answer_text_ru', ''),
                video_url_uz=row.get('video_url_uz', ''),
                video_url_ru=row.get('video_url_ru', '')
            )

            created_count += 1

        return Response({
            "success": True,
            "created": created_count,
            "skipped": skipped
        }, status=status.HTTP_201_CREATED)