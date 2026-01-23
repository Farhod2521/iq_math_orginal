import os

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

import django

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django_app.app_chat import routing as chat_routing
from django_app.app_chat.middleware import JwtAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddlewareStack(
        URLRouter(chat_routing.websocket_urlpatterns)
    ),
})
