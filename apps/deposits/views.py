from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deposits.models import Deposit
from apps.deposits.serializers import DepositSerializer
from apps.months.models import Month
from apps.users.permissions import HasCapability


class DepositListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            self.required_capability = 'deposit.approve' if request.user.has_capability('deposit.approve') and request.query_params.get('month') else 'deposit.view_own'
        elif request.method == 'POST':
            self.required_capability = 'deposit.submit'
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.user.has_capability('deposit.approve') and request.query_params.get('month'):
            qs = Deposit.objects.select_related('member', 'month').filter(month_id=request.query_params['month'])
        else:
            qs = Deposit.objects.select_related('member', 'month').filter(member=request.user)
        return Response(DepositSerializer(qs.order_by('-submitted_at'), many=True).data)

    def post(self, request):
        serializer = DepositSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            deposit = serializer.save()
            return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise


class DepositActionView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'deposit.approve'
    action = None

    def post(self, request, pk):
        action = self.action
        deposit = get_object_or_404(Deposit, pk=pk)
        if deposit.month.status != Month.Status.OPEN:
            return Response({'code': 'month_closed'}, status=status.HTTP_400_BAD_REQUEST)
        if deposit.status != Deposit.Status.PENDING:
            return Response({'code': 'deposit_not_pending'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            deposit.status = Deposit.Status.APPROVED
            deposit.processed_at = timezone.now()
            deposit.processed_by = request.user
            deposit.save(update_fields=['status', 'processed_at', 'processed_by'])
            return Response(DepositSerializer(deposit).data)

        if action == 'reject':
            reason = request.data.get('reason')
            if not reason:
                return Response({'code': 'reason_required'}, status=status.HTTP_400_BAD_REQUEST)
            deposit.status = Deposit.Status.REJECTED
            deposit.rejection_reason = reason
            deposit.processed_at = timezone.now()
            deposit.processed_by = request.user
            deposit.save(update_fields=['status', 'rejection_reason', 'processed_at', 'processed_by'])
            return Response(DepositSerializer(deposit).data)

        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
