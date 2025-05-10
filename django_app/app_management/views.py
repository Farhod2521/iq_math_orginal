from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ
from .serializers import SystemSettingsSerializer, FAQSerializer

class SystemSettingsListView(ListAPIView):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer


class FAQListView(ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer