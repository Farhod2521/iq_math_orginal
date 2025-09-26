from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage
from django.utils.http import quote
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from openpyxl import Workbook
import pytz
from django.db.models import Q
from .models import User, Student, Teacher, Parent, Tutor, StudentLoginHistory
from django_app.app_payments.models import Payment
from django.utils import timezone
def escape_uri_path(path):
    """Fayl nomini URLga moslashtirish"""
    return quote(path)
class All_Role_ListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ashgabat_tz = pytz.timezone("Asia/Ashgabat")
        export_excel = request.GET.get("export") == "excel"
        
        # --- FILTER PARAMETERS ---
        role = request.GET.get("role", "").strip()  # student, teacher, parent, tutor
        search_query = request.GET.get("search", "").strip()
        class_num = request.GET.get("class_num", "").strip() if role == 'student' else ""
        subject_name = request.GET.get("subject_name", "").strip() if role == 'student' else ""
        status_filter = request.GET.get("status", "").strip()  # active, inactive, all

        # --- BASE QUERY ---
        users = User.objects.all().order_by('-date_joined')
        
        # --- ROLE FILTER ---
        if role and role != 'all':
            users = users.filter(role=role)
        
        # --- SEARCH FILTER ---
        if search_query:
            users = users.filter(
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(student_profile__full_name__icontains=search_query) |
                Q(teacher_profile__full_name__icontains=search_query) |
                Q(parent_profile__full_name__icontains=search_query) |
                Q(tutor_profile__full_name__icontains=search_query)
            )
        
        # --- STATUS FILTER ---
        if status_filter == 'active':
            users = users.filter(
                Q(student_profile__status=True) | 
                Q(teacher_profile__status=True) | 
                Q(parent_profile__status=True) | 
                Q(tutor_profile__status=True)
            )
        elif status_filter == 'inactive':
            users = users.filter(
                Q(student_profile__status=False) | 
                Q(teacher_profile__status=False) | 
                Q(parent_profile__status=False) | 
                Q(tutor_profile__status=False)
            )

        data_json = []
        data_excel = []

        for idx, user in enumerate(users, start=1):
            profile_data = self.get_profile_data(user, ashgabat_tz)
            if profile_data:
                # JSON data - profile_id ni qo'shamiz
                data_json.append({
                    "id": profile_data['json'].get('profile_id', user.id),  # profile_id bo'lsa ishlatamiz, bo'lmasa user.id
                    "user_id": user.id,  # asl user id ni ham saqlab qo'yamiz
                    "role": user.role,
                    "phone": user.phone,
                    "email": user.email,
                    **{k: v for k, v in profile_data['json'].items() if k != 'profile_id'}
                })

                # Excel data
                data_excel.append({
                    "ID": idx,
                    "Profil ID": profile_data['excel'].get('profile_id', user.id),  # Excel uchun ham profile_id
                    "Roli": self.get_role_display(user.role),
                    "F.I.Sh.": profile_data['excel'].get('full_name', ''),
                    "Telefon": user.phone,
                    "Email": user.email or '',
                    "Viloyat": profile_data['excel'].get('region', ''),
                    "Tuman": profile_data['excel'].get('districts', ''),
                    "Manzil": profile_data['excel'].get('address', ''),
                    "Holati": profile_data['excel'].get('status_display', ''),
                    "Ro‘yxatdan o‘tgan sana": profile_data['excel'].get('registration_date', ''),
                    "Ro‘yxatdan o‘tgan vaqt": profile_data['excel'].get('registration_time', ''),
                    **profile_data['excel'].get('extra_fields', {})
                })

        # --- EXPORT TO EXCEL ---
        if export_excel:
            if not data_excel:
                return Response({"error": "Eksport qilish uchun ma'lumot topilmadi"}, status=status.HTTP_404_NOT_FOUND)
                
            wb = Workbook()
            ws = wb.active
            ws.title = "Foydalanuvchilar ro'yxati"

            headers = list(data_excel[0].keys()) if data_excel else []
            ws.append(headers)

            for row in data_excel:
                ws.append(list(row.values()))

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = escape_uri_path("Foydalanuvchilar_royxati.xlsx")
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            wb.save(response)
            return response

        # --- PAGINATION ---
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 10))

        paginator = Paginator(data_json, size)
        total_count = paginator.count
        total_pages = paginator.num_pages

        try:
            current_page = paginator.page(page)
        except EmptyPage:
            return Response({
                "error": "Page not found",
                "page": page,
                "size": size,
                "total": total_count,
                "total_pages": total_pages,
                "results": []
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "page": page,
            "size": size,
            "total": total_count,
            "total_pages": total_pages,
            "results": current_page.object_list
        })

    def get_profile_data(self, user, timezone):
        """Foydalanuvchi roliga qarab profil ma'lumotlarini olish"""
        
        profile_data = {
            'json': {},
            'excel': {}
        }

        if user.role == 'student' and hasattr(user, 'student_profile'):
            student = user.student_profile
            student_datetime = student.student_date.astimezone(timezone) if student.student_date else None

            # Login history
            last_login_obj = StudentLoginHistory.objects.filter(student=student).order_by('-login_time').first()
            last_login_formatted = last_login_obj.login_time.astimezone(timezone).strftime('%d/%m/%Y %H:%M') if last_login_obj else None

            # 🔹 Subscription ma’lumotlari
            subscription = getattr(student, 'subscription', None)
            now = timezone.now()
            days_until_next_payment = 0
            end_date_formatted = None

            if subscription and subscription.end_date:
                if now < subscription.end_date:
                    days_until_next_payment = (subscription.end_date - now).days
                end_date_formatted = subscription.end_date.strftime("%d/%m/%Y")

            # 🔹 Oxirgi to‘lov summasi
            last_payment = Payment.objects.filter(student=student, status="success").order_by('-payment_date').first()
            last_payment_amount = float(last_payment.amount) if last_payment else 0

            profile_data['json'] = {
                "profile_id": student.id,  # Student profil id sini qaytaramiz
                "full_name": student.full_name,
                "region": student.region,
                "districts": student.districts,
                "address": student.address,
                "brithday": student.brithday,
                "academy_or_school": student.academy_or_school,
                "academy_or_school_name": student.academy_or_school_name,
                "class_num": student.class_name.classes.name if student.class_name else None,
                "subject_name_uz": student.class_name.name_uz if student.class_name else None,
                "subject_name_ru": student.class_name.name_ru if student.class_name else None,
                "document_type": student.document_type,
                "document": student.document,
                "type_of_education": student.type_of_education,
                "status": student.status,
                "registration_date": student_datetime.strftime('%Y-%m-%d') if student_datetime else None,
                "registration_time": student_datetime.strftime('%H:%M:%S') if student_datetime else None,
                "last_login_time": last_login_formatted,

                # 🔹 Qo‘shimcha maydonlar:
                "days_until_next_payment": days_until_next_payment,
                "end_date": end_date_formatted,
                "last_payment_amount": last_payment_amount,
            }

            profile_data['excel'] = {
                'profile_id': student.id,  # Excel uchun ham profile_id
                'full_name': student.full_name,
                'region': student.region,
                'districts': student.districts,
                'address': student.address,
                'status_display': 'Aktiv' if student.status else 'Noaktiv',
                'registration_date': student_datetime.strftime('%Y-%m-%d') if student_datetime else '',
                'registration_time': student_datetime.strftime('%H:%M:%S') if student_datetime else '',
                'extra_fields': {
                    'Tug‘ilgan kun': student.brithday,
                    'Ta\'lim muassasasi': student.academy_or_school_name,
                    'Sinf': student.class_name.classes.name if student.class_name else '',
                    'Fan': student.class_name.name_uz if student.class_name else '',
                    'Oxirgi kirish': last_login_formatted or ''
                }
            }

        elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            teacher_datetime = teacher.teacher_date.astimezone(timezone) if teacher.teacher_date else None

            profile_data['json'] = {
                "profile_id": teacher.id,  # Teacher profil id sini qaytaramiz
                "full_name": teacher.full_name,
                "region": teacher.region,
                "districts": teacher.districts,
                "address": teacher.address,
                "brithday": teacher.brithday,
                "document_type": teacher.document_type,
                "document": teacher.document,
                "status": teacher.status,
                "is_verified_teacher": teacher.is_verified_teacher,
                "registration_date": teacher_datetime.strftime('%Y-%m-%d') if teacher_datetime else None,
                "registration_time": teacher_datetime.strftime('%H:%M:%S') if teacher_datetime else None
            }

            profile_data['excel'] = {
                'profile_id': teacher.id,  # Excel uchun ham profile_id
                'full_name': teacher.full_name,
                'region': teacher.region,
                'districts': teacher.districts,
                'address': teacher.address,
                'status_display': 'Aktiv' if teacher.status else 'Noaktiv',
                'registration_date': teacher_datetime.strftime('%Y-%m-%d') if teacher_datetime else '',
                'registration_time': teacher_datetime.strftime('%H:%M:%S') if teacher_datetime else '',
                'extra_fields': {
                    'Tasdiqlangan': 'Ha' if teacher.is_verified_teacher else 'Yo‘q',
                    'Tug‘ilgan kun': teacher.brithday,
                    'Hujjat turi': teacher.document_type,
                    'Hujjat raqami': teacher.document
                }
            }

        elif user.role == 'parent' and hasattr(user, 'parent_profile'):
            parent = user.parent_profile
            parent_datetime = parent.parent_date.astimezone(timezone) if parent.parent_date else None

            profile_data['json'] = {
                "profile_id": parent.id,  # Parent profil id sini qaytaramiz
                "full_name": parent.full_name,
                "region": parent.region,
                "districts": parent.districts,
                "address": parent.address,
                "status": parent.status,
                "registration_date": parent_datetime.strftime('%Y-%m-%d') if parent_datetime else None,
                "registration_time": parent_datetime.strftime('%H:%M:%S') if parent_datetime else None
            }

            profile_data['excel'] = {
                'profile_id': parent.id,  # Excel uchun ham profile_id
                'full_name': parent.full_name,
                'region': parent.region or '',
                'districts': parent.districts or '',
                'address': parent.address or '',
                'status_display': 'Aktiv' if parent.status else 'Noaktiv',
                'registration_date': parent_datetime.strftime('%Y-%m-%d') if parent_datetime else '',
                'registration_time': parent_datetime.strftime('%H:%M:%S') if parent_datetime else '',
                'extra_fields': {}
            }

        elif user.role == 'tutor' and hasattr(user, 'tutor_profile'):
            tutor = user.tutor_profile
            tutor_datetime = tutor.tutor_date.astimezone(timezone) if tutor.tutor_date else None

            profile_data['json'] = {
                "profile_id": tutor.id,  # Tutor profil id sini qaytaramiz
                "full_name": tutor.full_name,
                "region": tutor.region,
                "districts": tutor.districts,
                "address": tutor.address,
                "status": tutor.status,
                "registration_date": tutor_datetime.strftime('%Y-%m-%d') if tutor_datetime else None,
                "registration_time": tutor_datetime.strftime('%H:%M:%S') if tutor_datetime else None
            }

            profile_data['excel'] = {
                'profile_id': tutor.id,  # Excel uchun ham profile_id
                'full_name': tutor.full_name,
                'region': tutor.region or '',
                'districts': tutor.districts or '',
                'address': tutor.address or '',
                'status_display': 'Aktiv' if tutor.status else 'Noaktiv',
                'registration_date': tutor_datetime.strftime('%Y-%m-%d') if tutor_datetime else '',
                'registration_time': tutor_datetime.strftime('%H:%M:%S') if tutor_datetime else '',
                'extra_fields': {}
            }

        else:
            # Admin yoki profil topilmagan foydalanuvchilar uchun
            user_datetime = user.date_joined.astimezone(timezone) if user.date_joined else None
            
            profile_data['json'] = {
                "profile_id": user.id,  # Admin uchun user.id ni qaytaramiz
                "full_name": user.get_full_name() or "Admin",
                "registration_date": user_datetime.strftime('%Y-%m-%d') if user_datetime else None,
                "registration_time": user_datetime.strftime('%H:%M:%S') if user_datetime else None
            }

            profile_data['excel'] = {
                'profile_id': user.id,  # Excel uchun ham user.id
                'full_name': user.get_full_name() or "Admin",
                'region': '',
                'districts': '',
                'address': '',
                'status_display': 'Aktiv',
                'registration_date': user_datetime.strftime('%Y-%m-%d') if user_datetime else '',
                'registration_time': user_datetime.strftime('%H:%M:%S') if user_datetime else '',
                'extra_fields': {}
            }

        return profile_data

    def get_role_display(self, role):
        """Rolni ko'rinishli qilib qaytarish"""
        role_displays = {
            'student': 'O‘quvchi',
            'teacher': 'O‘qituvchi',
            'parent': 'Ota-ona',
            'tutor': 'Tarbiyachi',
            'admin': 'Administrator'
        }
        return role_displays.get(role, role)