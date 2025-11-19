from django.apps import AppConfig

class AppManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_app.app_management'
    
    def ready(self):
        import django_app.app_management.signals