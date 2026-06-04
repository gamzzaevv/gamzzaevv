from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.events.models import PromoCode


class ValidatePromoView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code", "").upper().strip()
        if not code:
            return Response({"valid": False, "message": "Введите промокод"})
        try:
            promo = PromoCode.objects.get(code=code)
        except PromoCode.DoesNotExist:
            return Response({"valid": False, "message": "Промокод не найден"})

        if not promo.is_valid():
            return Response({"valid": False, "message": "Промокод недействителен или истёк"})

        if promo.discount_type == PromoCode.DISCOUNT_PERCENT:
            label = f"Скидка {promo.discount_value}%"
        else:
            label = f"Скидка {promo.discount_value} ₽"

        return Response({"valid": True, "message": label, "discount_type": promo.discount_type})
