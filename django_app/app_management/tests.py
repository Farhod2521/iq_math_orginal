from types import SimpleNamespace

from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from django_app.app_management.models import SystemSettings


class SystemSettingsCRUDAPITestCase(APITransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if SystemSettings._meta.db_table not in connection.introspection.table_names():
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(SystemSettings)

    def setUp(self):
        self.url = reverse("system-settings-crud")
        self.teacher = SimpleNamespace(
            role="teacher",
            is_authenticated=True,
        )
        self.superadmin = SimpleNamespace(
            role="superadmin",
            is_authenticated=True,
        )
        self.student = SimpleNamespace(
            role="student",
            is_authenticated=True,
        )

    def test_teacher_can_create_update_delete_and_recreate_system_settings(self):
        self.client.force_authenticate(user=self.teacher)

        create_response = self.client.post(
            self.url,
            {
                "about_uz": "Biz haqimizda matni",
                "about_ru": "О нас",
                "instagram_link": "https://instagram.com/iqmath",
                "telegram_link": "https://t.me/iqmath",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SystemSettings.objects.count(), 1)
        self.assertEqual(SystemSettings.objects.get().about, "Biz haqimizda matni")

        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["about_uz"], "Biz haqimizda matni")
        self.assertEqual(get_response.data["about_ru"], "О нас")

        update_response = self.client.put(
            self.url,
            {"about": "Yangilangan matn"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(SystemSettings.objects.get().about, "Yangilangan matn")

        delete_response = self.client.delete(self.url)
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(SystemSettings.objects.count(), 0)

        recreate_response = self.client.post(
            self.url,
            {"about_uz": "Qayta yaratildi"},
            format="json",
        )
        self.assertEqual(recreate_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_second_post_is_blocked_when_settings_already_exists(self):
        self.client.force_authenticate(user=self.teacher)
        SystemSettings.objects.create(about="Birinchi sozlama", about_uz="Birinchi sozlama")

        response = self.client.post(
            self.url,
            {"about_uz": "Ikkinchi sozlama"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_student_cannot_manage_system_settings(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_read_existing_system_settings(self):
        SystemSettings.objects.create(
            about="Superadmin uchun sozlama",
            about_uz="Superadmin uchun sozlama",
            about_ru="Настройки для superadmin",
        )
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["about_uz"], "Superadmin uchun sozlama")
