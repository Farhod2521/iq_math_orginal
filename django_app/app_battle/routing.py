from django.urls import path
from .consumers import BattleConsumer

websocket_urlpatterns = [
    path("ws/battle/<int:room_id>/", BattleConsumer.as_asgi()),
]
