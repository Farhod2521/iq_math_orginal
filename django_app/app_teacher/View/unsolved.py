from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_app.app_teacher.models import  UnsolvedQuestionReport

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
