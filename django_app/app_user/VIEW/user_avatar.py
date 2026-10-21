"""
Profil rasmi (mobil ilova va sayt uchun).

POST   /api/v1/auth/user/avatar/   multipart: file=<rasm>   — rasmni o'rnatadi/almashtiradi
DELETE /api/v1/auth/user/avatar/                            — rasmni olib tashlaydi

Javob: {"avatar": "<to'liq URL>", "data": {"filename": "<to'liq URL>"}}
("data.filename" — mobil ilovaning eski upload javobi formati bilan moslik uchun)
"""
import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
AVATAR_SIZE = 512  # px, kvadrat


def _avatar_url(request, user):
    return request.build_absolute_uri(user.avatar.url) if user.avatar else None


class UserAvatarAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("avatar")
        if not upload:
            return Response({"message": "Rasm yuborilmadi."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_UPLOAD_BYTES:
            return Response({"message": "Rasm hajmi 10 MB dan oshmasligi kerak."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image = Image.open(upload)
            image = ImageOps.exif_transpose(image)  # telefon kamerasidagi burilishni to'g'rilash
            image = ImageOps.fit(image.convert("RGB"), (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
        except (UnidentifiedImageError, OSError):
            return Response({"message": "Fayl rasm emas yoki buzilgan."}, status=status.HTTP_400_BAD_REQUEST)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True)

        user = request.user
        old = user.avatar.name if user.avatar else None
        user.avatar.save(f"{user.id}_{uuid.uuid4().hex[:8]}.jpg", ContentFile(buffer.getvalue()), save=True)
        if old:
            user.avatar.storage.delete(old)

        url = _avatar_url(request, user)
        return Response({"avatar": url, "data": {"filename": url}, "message": "Profil rasmi yangilandi."})

    def delete(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response({"avatar": None, "message": "Profil rasmi olib tashlandi."})
