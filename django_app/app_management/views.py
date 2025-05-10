from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ, Product
from .serializers import SystemSettingsSerializer, FAQSerializer, ProductSerializer

class SystemSettingsListView(ListAPIView):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer


class FAQListView(ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer