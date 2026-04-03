from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework import serializers
from django_app.app_payments.models import SubscriptionSetting


class SubscriptionSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionSetting
        fields = ['id', 'free_trial_days']


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) == "superadmin"
        )


class SubscriptionSettingCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    # GET — list yoki detail
    def get(self, request, pk=None):
        if pk:
            try:
                obj = SubscriptionSetting.objects.get(pk=pk)
            except SubscriptionSetting.DoesNotExist:
                return Response({"error": "SubscriptionSetting topilmadi."}, status=404)
            return Response(SubscriptionSettingSerializer(obj).data)

        queryset = SubscriptionSetting.objects.all()
        return Response(SubscriptionSettingSerializer(queryset, many=True).data)

    # POST — yaratish
    def post(self, request):
        serializer = SubscriptionSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Obuna sozlamasi yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    # PUT — yangilash (partial)
    def put(self, request, pk):
        try:
            obj = SubscriptionSetting.objects.get(pk=pk)
        except SubscriptionSetting.DoesNotExist:
            return Response({"error": "SubscriptionSetting topilmadi."}, status=404)

        serializer = SubscriptionSettingSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Obuna sozlamasi yangilandi.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    # DELETE — o'chirish
    def delete(self, request, pk):
        try:
            obj = SubscriptionSetting.objects.get(pk=pk)
        except SubscriptionSetting.DoesNotExist:
            return Response({"error": "SubscriptionSetting topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Obuna sozlamasi o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
