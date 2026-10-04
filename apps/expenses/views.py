from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.models import Expense
from apps.expenses.serializers import ExpenseSerializer
from apps.months.models import Month
from apps.users.permissions import HasCapability

class ExpenseListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'expense.create'

    def get(self, request):
        if not request.query_params.get('month'):
            qs = Expense.objects.filter(is_deleted=False)
        else:
            qs = Expense.objects.filter(month_id=request.query_params['month'], is_deleted=False)
        return Response(ExpenseSerializer(qs.order_by('-expense_date'), many=True).data)

    def post(self, request):
        open_month = Month.objects.filter(status=Month.Status.OPEN).order_by('-start_date').first()
        if open_month is None:
            return Response({'code': 'no_open_month'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExpenseSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            expense = serializer.save(month=open_month, created_by=request.user)
            return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise

class ExpenseDetailView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'expense.update'

    def patch(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        if expense.month.status != Month.Status.OPEN:
            return Response({'code': 'month_not_open'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExpenseSerializer(expense, data=request.data, partial=True, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(ExpenseSerializer(expense).data)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise

class ExpenseDeleteView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'expense.delete'

    def delete(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk, is_deleted=False)
        reason = request.data.get('reason')
        if not reason:
            return Response({'code': 'reason_required'}, status=status.HTTP_400_BAD_REQUEST)
        if expense.month.status != Month.Status.OPEN:
            return Response({'code': 'month_not_open'}, status=status.HTTP_400_BAD_REQUEST)
        expense.is_deleted = True
        expense.deleted_at = timezone.now()
        expense.deleted_by = request.user
        expense.delete_reason = reason
        expense.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'])
        return Response({'status': 'deleted'})


