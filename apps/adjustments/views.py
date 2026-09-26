from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.adjustments.models import Adjustment
from apps.adjustments.serializers import AdjustmentSerializer
from apps.months.models import Month
from apps.users.permissions import HasCapability


class AdjustmentListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'adjustment.create'

    def get(self, request):
        qs = Adjustment.objects.select_related('member', 'month', 'created_by').all()
        return Response(AdjustmentSerializer(qs.order_by('-created_at'), many=True).data)

    def post(self, request):
        serializer = AdjustmentSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            adjustment = serializer.save()
            return Response(AdjustmentSerializer(adjustment).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise
