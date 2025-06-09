from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_app.app_teacher.models import  UnsolvedQuestionReport
from django.utils import timezone
class TeacherUnsolvedQuestionReportListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            teacher = request.user.teacher_profile  
        except AttributeError:
            return Response({"error": "Siz o‘qituvchi emassiz"}, status=status.HTTP_403_FORBIDDEN)
        reports = UnsolvedQuestionReport.objects.filter(teachers=teacher).order_by('-created_at').distinct()

        data = []
        for report in reports:
            data.append({
                "id": report.id,
                "question": str(report.question),
                "student": str(report.student),
                "message": report.message,
                "status": report.status,
                "answer": report.answer if report.answer else "",
                "answered_by": str(report.answered_by) if report.answered_by else None,
                "created_at": report.created_at,
                "answered_at": report.answered_at,
            })

        return Response(data, status=status.HTTP_200_OK)


class TeacherAnswerUnsolvedQuestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            teacher = request.user.teacher_profile
        except AttributeError:
            return Response({"error": "Siz o‘qituvchi emassiz"}, status=status.HTTP_403_FORBIDDEN)

        report_id = request.data.get("report_id")
        answer = request.data.get("answer")

        if not report_id or not answer:
            return Response({"error": "report_id va answer maydonlari majburiy"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = UnsolvedQuestionReport.objects.get(id=report_id, teachers=teacher)
        except UnsolvedQuestionReport.DoesNotExist:
            return Response({"error": "Bu misol sizga tegishli emas yoki mavjud emas"}, status=status.HTTP_404_NOT_FOUND)

        # Javob yozish
        report.answer = answer
        report.answered_by = teacher
        report.status = "answered"
        report.answered_at = timezone.now()
        report.save()

        return Response({"success": "Javob muvaffaqiyatli yozildi"}, status=status.HTTP_200_OK)
    

