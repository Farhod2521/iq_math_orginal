import random
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django_app.app_user.models import Student
from django_app.app_student.models import StudentScore, SomTransferLog
from django_app.app_user.sms_service import send_sms


class SomTransferRequestAPIView(APIView):
    """
    1-qadam: So'm o'tkazish so'rovi.
    Qabul qiluvchi identification raqami va summani yuboring.
    Yuboruvchining telefoniga 5 xonali OTP keladi.

    POST /student/som-transfer/request/
    {
        "receiver_identification": "202505070001",
        "amount": 5000
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        receiver_identification = request.data.get("receiver_identification")
        amount = request.data.get("amount")

        if not receiver_identification or not amount:
            return Response(
                {"error": "receiver_identification va amount majburiy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response({"error": "amount butun son bo'lishi kerak."}, status=400)

        if amount <= 0:
            return Response({"error": "So'm miqdori 0 dan katta bo'lishi kerak."}, status=400)

        # Yuboruvchini aniqlash
        try:
            sender = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"error": "Student profili topilmadi."}, status=404)

        # Qabul qiluvchini aniqlash
        try:
            receiver = Student.objects.get(identification=receiver_identification)
        except Student.DoesNotExist:
            return Response({"error": "Bu identification raqamli student topilmadi."}, status=404)

        if sender.id == receiver.id:
            return Response({"error": "O'zingizga so'm o'tkaza olmaysiz."}, status=400)

        # Balansni tekshirish
        try:
            sender_score = StudentScore.objects.get(student=sender)
        except StudentScore.DoesNotExist:
            return Response({"error": "Sizning balans ma'lumotingiz topilmadi."}, status=404)

        if sender_score.som < amount:
            return Response(
                {"error": f"Balansingizda yetarli so'm yo'q. Mavjud: {sender_score.som} so'm."},
                status=400
            )

        # Eski pending transferlarni bekor qilish
        SomTransferLog.objects.filter(
            sender=sender, is_confirmed=False, is_expired=False
        ).update(is_expired=True)

        # OTP generatsiya
        otp_code = str(random.randint(10000, 99999))

        # Log yozish (pending holat)
        transfer = SomTransferLog.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            otp_code=otp_code,
        )

        # SMS yuborish
        send_sms(
            phone=sender.user.phone,
            sms_code=f"Pul o'tkazish tasdiqi. Kod: {otp_code}. {amount} so'm → {receiver.full_name}. Kodni hech kimga bermang."
        )

        return Response({
            "message": "SMS yuborildi. OTP kodni kiriting.",
            "transfer_id": transfer.id,
            "receiver_name": receiver.full_name,
            "amount": amount,
        }, status=status.HTTP_200_OK)


class SomTransferConfirmAPIView(APIView):
    """
    2-qadam: OTP kodni tasdiqlash va so'mni o'tkazish.

    POST /student/som-transfer/confirm/
    {
        "transfer_id": 1,
        "otp_code": "47382"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transfer_id = request.data.get("transfer_id")
        otp_code = request.data.get("otp_code")

        if not transfer_id or not otp_code:
            return Response(
                {"error": "transfer_id va otp_code majburiy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            sender = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"error": "Student profili topilmadi."}, status=404)

        try:
            transfer = SomTransferLog.objects.get(
                id=transfer_id, sender=sender, is_confirmed=False, is_expired=False
            )
        except SomTransferLog.DoesNotExist:
            return Response(
                {"error": "Transfer topilmadi yoki muddati o'tgan."},
                status=404
            )

        if transfer.otp_code != str(otp_code):
            return Response({"error": "OTP kod noto'g'ri."}, status=400)

        # Balanslarni qayta tekshirish
        try:
            sender_score = StudentScore.objects.get(student=sender)
        except StudentScore.DoesNotExist:
            return Response({"error": "Yuboruvchi balansi topilmadi."}, status=404)

        try:
            receiver_score = StudentScore.objects.get(student=transfer.receiver)
        except StudentScore.DoesNotExist:
            return Response({"error": "Qabul qiluvchi balansi topilmadi."}, status=404)

        if sender_score.som < transfer.amount:
            transfer.is_expired = True
            transfer.save()
            return Response(
                {"error": f"Balansingizda yetarli so'm yo'q. Mavjud: {sender_score.som} so'm."},
                status=400
            )

        # So'mni o'tkazish
        sender_score.som -= transfer.amount
        sender_score.save()

        receiver_score.som += transfer.amount
        receiver_score.save()

        # Transferni tasdiqlash
        transfer.is_confirmed = True
        transfer.confirmed_at = timezone.now()
        transfer.save()

        return Response({
            "message": "So'm muvaffaqiyatli o'tkazildi.",
            "sender": sender.full_name,
            "receiver": transfer.receiver.full_name,
            "amount": transfer.amount,
            "sender_balance_after": sender_score.som,
            "confirmed_at": transfer.confirmed_at,
        }, status=status.HTTP_200_OK)


class SomTransferHistoryAPIView(APIView):
    """
    Studentning so'm o'tkazish tarixi (yuborgan va qabul qilgan).

    GET /student/som-transfer/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"error": "Student topilmadi."}, status=404)

        sent = SomTransferLog.objects.filter(sender=student, is_confirmed=True)
        received = SomTransferLog.objects.filter(receiver=student, is_confirmed=True)

        def format_log(qs, direction):
            result = []
            for t in qs:
                result.append({
                    "id": t.id,
                    "direction": direction,
                    "other_party": t.receiver.full_name if direction == "sent" else t.sender.full_name,
                    "amount": t.amount,
                    "confirmed_at": t.confirmed_at,
                })
            return result

        return Response({
            "sent": format_log(sent, "sent"),
            "received": format_log(received, "received"),
        })
