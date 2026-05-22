import threading
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings


def _initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)


def send_push_notification(fcm_token, title, body, data=None):
    try:
        _initialize_firebase()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"FCM xatolik (token: {fcm_token[:20]}...): {e}")
        return False


def _send_to_all_students_task(title, body, data=None):
    from django_app.app_user.models import User
    tokens = (
        User.objects
        .filter(role='student', fcm_token__isnull=False)
        .exclude(fcm_token='')
        .values_list('fcm_token', flat=True)
    )
    for token in tokens:
        send_push_notification(token, title, body, data)


def send_push_to_all_students(title, body, data=None):
    """Barcha studentlarga background thread orqali notification yuboradi."""
    thread = threading.Thread(
        target=_send_to_all_students_task,
        args=(title, body, data),
        daemon=True,
    )
    thread.start()
