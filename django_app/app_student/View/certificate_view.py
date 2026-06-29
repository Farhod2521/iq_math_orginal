import io
import os
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

from django_app.app_user.models import User, Student
from django_app.app_student.models import StudentScore
from django_app.app_management.models import CertificateSettings

# ── Ranglar ────────────────────────────────────────────────────────────────
BLUE        = HexColor("#5B6DD5")
BLUE_LIGHT  = HexColor("#EEF0FB")
BLUE_DARK   = HexColor("#3A4BAD")
GOLD        = HexColor("#F5A623")
WHITE       = colors.white
GRAY        = HexColor("#6B7280")
DARK        = HexColor("#1F2937")

LOGO_PATH = os.path.join(settings.BASE_DIR, "Media", "iqmath_logo.png")


def _draw_certificate(student_name, score_rank, coin_rank, score_val, coin_val, top_count):
    """A4 portrait sertifikat PDF yaratadi, bytes qaytaradi."""
    buf = io.BytesIO()
    W, H = A4   # 595 x 842 pt

    c = canvas.Canvas(buf, pagesize=A4)

    # ── Fon ────────────────────────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Tashqi border ──────────────────────────────────────────────────────
    margin = 14 * mm
    c.setStrokeColor(BLUE)
    c.setLineWidth(3)
    c.roundRect(margin, margin, W - 2*margin, H - 2*margin, 8, fill=0, stroke=1)

    # ── Ichki border ───────────────────────────────────────────────────────
    inner = margin + 4
    c.setStrokeColor(BLUE_LIGHT)
    c.setLineWidth(1)
    c.roundRect(inner, inner, W - 2*inner, H - 2*inner, 6, fill=0, stroke=1)

    # ── Yuqori ko'k tasmа ──────────────────────────────────────────────────
    band_h = 52 * mm
    c.setFillColor(BLUE)
    c.roundRect(margin, H - margin - band_h, W - 2*margin, band_h, 8, fill=1, stroke=0)
    # pastki qismini to'g'ri qilamiz
    c.rect(margin, H - margin - band_h, W - 2*margin, band_h / 2, fill=1, stroke=0)

    # ── Logo ───────────────────────────────────────────────────────────────
    logo_size = 20 * mm
    logo_x = margin + 8 * mm
    logo_y = H - margin - band_h + (band_h - logo_size) / 2
    if os.path.exists(LOGO_PATH):
        c.drawImage(LOGO_PATH, logo_x, logo_y, width=logo_size, height=logo_size,
                    mask="auto", preserveAspectRatio=True)

    # ── IQ MATH matni (header) ─────────────────────────────────────────────
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(logo_x + logo_size + 6*mm, H - margin - band_h/2 + 3*mm, "IQ MATH")
    c.setFont("Helvetica", 10)
    c.drawString(logo_x + logo_size + 6*mm, H - margin - band_h/2 - 5*mm,
                 "Matematika ta'lim platformasi")

    # ── "TOP N" badge (o'ng tomonda) ───────────────────────────────────────
    badge_x = W - margin - 38*mm
    badge_y = H - margin - band_h + (band_h - 18*mm)/2
    c.setFillColor(GOLD)
    c.roundRect(badge_x, badge_y, 30*mm, 18*mm, 4, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(badge_x + 15*mm, badge_y + 11*mm, f"TOP {top_count}")
    c.setFont("Helvetica", 8)
    c.drawCentredString(badge_x + 15*mm, badge_y + 4*mm, "O'quvchi")

    # ── "SERTIFIKAT" sarlavha ──────────────────────────────────────────────
    title_y = H - margin - band_h - 28*mm
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(W/2, title_y, "SERTIFIKAT")

    # sarlavha ostidagi chiziq
    line_w = 80 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(W/2 - line_w/2, title_y - 4*mm, W/2 + line_w/2, title_y - 4*mm)

    # ── Taqdim etiladi matni ───────────────────────────────────────────────
    text_y = title_y - 18*mm
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, text_y, "Ushbu sertifikat taqdim etiladi")

    # ── Student ismi ───────────────────────────────────────────────────────
    name_y = text_y - 18*mm
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(W/2, name_y, student_name)

    # ism ostidagi chiziq
    c.setStrokeColor(BLUE_LIGHT)
    c.setLineWidth(1)
    c.line(margin + 20*mm, name_y - 4*mm, W - margin - 20*mm, name_y - 4*mm)

    # ── Asosiy matn ────────────────────────────────────────────────────────
    body_y = name_y - 22*mm
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 11)
    line1 = "IQ Math matematika ta'lim platformasida"
    line2 = f"TOP {top_count} eng yaxshi o'quvchilar qatoriga kirganligingiz"
    line3 = "munosabati bilan taqdirlanadi."
    c.drawCentredString(W/2, body_y,        line1)
    c.drawCentredString(W/2, body_y - 7*mm, line2)
    c.drawCentredString(W/2, body_y - 14*mm, line3)

    # ── Statistika kartochkalari ───────────────────────────────────────────
    card_y   = body_y - 40*mm
    card_w   = 60 * mm
    card_h   = 32 * mm
    gap      = 8 * mm
    total_w  = 2 * card_w + gap
    start_x  = (W - total_w) / 2

    def draw_stat_card(cx, label, value, rank):
        c.setFillColor(BLUE_LIGHT)
        c.roundRect(cx, card_y, card_w, card_h, 5, fill=1, stroke=0)
        c.setStrokeColor(BLUE)
        c.setLineWidth(1)
        c.roundRect(cx, card_y, card_w, card_h, 5, fill=0, stroke=1)

        # Label
        c.setFillColor(BLUE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(cx + card_w/2, card_y + card_h - 9*mm, label)

        # Qiymat
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(cx + card_w/2, card_y + card_h/2 - 2*mm, f"{value:,}")

        # O'rin
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(cx + card_w/2, card_y + 4*mm, f"#{rank}-o'rin")

    draw_stat_card(start_x,              "BALL",  score_val, score_rank)
    draw_stat_card(start_x + card_w + gap, "TANGA", coin_val,  coin_rank)

    # ── Pastki qism: sana + footer tasma ──────────────────────────────────
    from datetime import date
    today_str = date.today().strftime("%d.%m.%Y")

    footer_h = 18 * mm
    c.setFillColor(BLUE_LIGHT)
    c.rect(margin, margin, W - 2*margin, footer_h, fill=1, stroke=0)

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9)
    c.drawString(margin + 8*mm, margin + 7*mm, f"Sana: {today_str}")
    c.drawCentredString(W/2, margin + 7*mm, "iqmath.uz")
    c.drawRightString(W - margin - 8*mm, margin + 7*mm, "© IQ Math 2026")

    # ── Corner dekorlar ────────────────────────────────────────────────────
    star_size = 6 * mm
    for (sx, sy) in [
        (margin + 5*mm,     H - margin - 5*mm - star_size),
        (W - margin - 5*mm - star_size, H - margin - 5*mm - star_size),
    ]:
        c.setFillColor(GOLD)
        c.circle(sx + star_size/2, sy + star_size/2, star_size/2, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx + star_size/2, sy + star_size/2 - 3, "★")

    c.save()
    buf.seek(0)
    return buf.read()


class CertificateDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── 1. CertificateSettings ─────────────────────────────────────────
        settings_obj = CertificateSettings.objects.filter(is_active=True).first()
        if not settings_obj:
            return Response(
                {"error": "Sertifikat hozircha faol emas."},
                status=status.HTTP_403_FORBIDDEN
            )
        top_count = settings_obj.top_count

        # ── 2. Student ─────────────────────────────────────────────────────
        student_id = request.query_params.get("student_id")
        if student_id:
            try:
                student = Student.objects.select_related("user").get(id=student_id)
            except Student.DoesNotExist:
                return Response({"error": "Student topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        else:
            if not hasattr(request.user, "student_profile"):
                return Response(
                    {"error": "student_id parametrini yuboring yoki student sifatida kiring."},
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
