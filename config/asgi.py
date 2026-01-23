import os
import django

# 1️⃣ AVVAL settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2️⃣ KEYIN django setup (🔥 MUHIM)
django.setup()

# 3️⃣ ENDI xavfsiz importlar
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from django_app.app_chat import routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
