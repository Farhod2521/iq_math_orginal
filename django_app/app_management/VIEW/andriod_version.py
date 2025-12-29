from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_app.app_management.models import  AndroidVersion
from django_app.app_management.serializers import AndroidVersionSerializer

class AndroidVersionAPIView(APIView):
    """
    BAZADA FAQAT BITTA YOZUV BO‘LADI
    """

    def get_object(self):
        obj, created = AndroidVersion.objects.get_or_create(
            id=1,
            defaults={
                "android_latest_version": "1.0.0",
                "android_force_update": False,
                "ios_latest_version": "1.0.0",
                "ios_force_update": False,
            }
        )
        return obj

    # 📥 CLIENT UCHUN (ANDROID / IOS)
    def get(self, request):
        obj = self.get_object()
        serializer = AndroidVersionSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 🛠 ADMIN UCHUN (UPDATE)
    def put(self, request):
        obj = self.get_object()
        serializer = AndroidVersionSerializer(
            obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST ham PUT bilan bir xil ishlaydi
    def post(self, request):
        return self.put(request)
