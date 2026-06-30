import io
import os
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader, PdfWriter

from django_app.app_user.models import User, Student
from django_app.app_student.models import StudentScore
from django_app.app_management.models import CertificateSettings

# ── Ranglar ────────────────────────────────────────────────────────────────
BLUE_DARK = HexColor("#1F2A6B")
DARK      = HexColor("#1F2937")

# ── Tayyor shablon (fon) ─────────────────────────────────────────────────
TEMPLATE_PATH = os.path.join(settings.BASE_DIR, "Media", "certificate", "certificate_template.pdf")

# Shablondagi statik matnlarning (pdfplumber bilan o'lchangan) koordinatalari.
# Shablon o'zgarsa, shu koordinatalarni qayta o'lchash kerak bo'ladi.
NAME_LINE_X_RANGE = (184.2, 658.0)   # ism yoziladigan bo'sh chiziq
TOP_DASH_END_X    = 652             # "TOP-" so'zi tugagan joy, raqam shu yerdan boshlanadi
BALL_ICON_X_RANGE = (398.4, 460.1)  # "BALL" belgisi joylashgan x oralig'i
TANGA_ICON_X_RANGE = (652.3, 737.3)  # "TANGA" belgisi joylashgan x oralig'i


def _fit_font_size(text, font_name, max_size, max_width):
    """Matn berilgan kenglikka sig'maguncha shrift hajmini kichraytiradi."""
    size = max_size
    while size > 10 and stringWidth(text, font_name, size) > max_width:
        size -= 1
    return size


def _build_overlay(W, H, student_name, top_count, score_val, coin_val):
    """Shablon ustiga yoziladigan matnlarni o'z ichiga olgan shaffof PDF qatlam yaratadi."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # ── Student ismi — bo'sh chiziq ustida (NAME_LINE_X_RANGE) ─────────────
    name_font = "Helvetica-Bold"
    max_name_width = (NAME_LINE_X_RANGE[1] - NAME_LINE_X_RANGE[0]) - 20
    name_size = _fit_font_size(student_name, name_font, 24, max_name_width)
    c.setFillColor(BLUE_DARK)
    c.setFont(name_font, name_size)
    name_y = H - 282
    c.drawCentredString(sum(NAME_LINE_X_RANGE) / 2, name_y, student_name)

    # ── "TOP-" so'zidan keyingi raqam ───────────────────────────────────────
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 19)
    c.drawString(TOP_DASH_END_X, H - 323, f"{top_count}")

    # ── BALL va TANGA qiymatlari ────────────────────────────────────────────
    c.setFillColor(BLUE_DARK)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(sum(BALL_ICON_X_RANGE) / 2, H - 485, f"{score_val:,}")
    c.drawCentredString(sum(TANGA_ICON_X_RANGE) / 2, H - 485, f"{coin_val:,}")

    c.save()
    buf.seek(0)
    return buf


def _draw_certificate(student_name, score_rank, coin_rank, score_val, coin_val, top_count):
    """Tayyor shablon (Media/certificate/certificate_template.pdf) ustiga
    student ma'lumotlarini yozib, yakuniy sertifikat PDF bytes qaytaradi."""
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Sertifikat shabloni topilmadi: {TEMPLATE_PATH}")

    reader = PdfReader(TEMPLATE_PATH)
    page = reader.pages[0]
    W = float(page.mediabox.width)
    H = float(page.mediabox.height)

    overlay_buf = _build_overlay(W, H, student_name, top_count, score_val, coin_val)
    overlay_page = PdfReader(overlay_buf).pages[0]
    page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    out_buf.seek(0)
    return out_buf.read()


class CertificateDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ── 1. CertificateSettings ─────────────────────────────────────────
        settings_obj = CertificateSettings.objects.filter(is_active=True).first()
        if not settings_obj:
            return Response(
                {"error": "Sertifikat hozircha faol emas."},
                status=status.HTTP_403_FORBIDDEN
            )
        top_count = settings_obj.top_count

        # ── 2. Student ─────────────────────────────────────────────────────
        student_id = request.data.get("student_id")
        if student_id:
            try:
                student = Student.objects.select_related("user").get(id=student_id)
            except Student.DoesNotExist:
                return Response({"error": "Student topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        else:
            if not hasattr(request.user, "student_profile"):
                return Response(
                    {"error": "student_id yuborilmadi yoki student sifatida kiring."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            student = request.user.student_profile

        # ── 3. Reyting hisoblash ───────────────────────────────────────────
        all_scores = StudentScore.objects.order_by("-score").values_list("student_id", flat=True)
        score_ranking = list(all_scores)

        all_coins = StudentScore.objects.order_by("-coin").values_list("student_id", flat=True)
        coin_ranking = list(all_coins)

        try:
            score_rank = score_ranking.index(student.id) + 1
        except ValueError:
            score_rank = None

        try:
            coin_rank = coin_ranking.index(student.id) + 1
        except ValueError:
            coin_rank = None

        in_top_score = score_rank is not None and score_rank <= top_count
        in_top_coin  = coin_rank  is not None and coin_rank  <= top_count

        if not (in_top_score or in_top_coin):
            return Response(
                {
                    "error": f"Siz TOP {top_count} ichida emassiz.",
                    "score_rank": score_rank,
                    "coin_rank":  coin_rank,
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # ── 4. Qiymatlar ───────────────────────────────────────────────────
        try:
            score_obj = StudentScore.objects.get(student=student)
            score_val = score_obj.score
            coin_val  = score_obj.coin
        except StudentScore.DoesNotExist:
            score_val, coin_val = 0, 0

        display_rank_score = score_rank if score_rank else "-"
        display_rank_coin  = coin_rank  if coin_rank  else "-"

        # ── 5. PDF yaratish ────────────────────────────────────────────────
        pdf_bytes = _draw_certificate(
            student_name=student.full_name,
            score_rank=display_rank_score,
            coin_rank=display_rank_coin,
            score_val=score_val,
            coin_val=coin_val,
            top_count=top_count,
        )

        safe_name = student.full_name.replace(" ", "_")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="IQMath_Sertifikat_{safe_name}.pdf"'
        )
        return response
