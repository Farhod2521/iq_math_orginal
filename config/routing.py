from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django_app import app_chat

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(
            app_chat.routing.websocket_urlpatterns
        )
    ),
})

