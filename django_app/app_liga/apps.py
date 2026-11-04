from django.apps import AppConfig


class AppLigaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_app.app_liga'
    verbose_name = "Matematik Liga"

    def ready(self):
        import django_app.app_liga.signals  # noqa: F401
