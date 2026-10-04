from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.guest_meals.models import GuestMeal
from apps.guest_meals.serializers import GuestMealSerializer
from apps.months.utils import NoMonthForDateError
from apps.users.permissions import HasCapability


class GuestMealListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)

    def initial(self, request, *args, **kwargs):
        self.perform_authentication(request)
        if request.method == 'GET':
            self.required_capability = 'guest_meal.approve' if request.user.has_capability('guest_meal.approve') and request.GET.get('month') else 'guest_meal.view_own'
        elif request.method == 'POST':
            self.required_capability = 'guest_meal.submit'
        super().initial(request, *args, **kwargs)
        
    def get(self, request):
        if request.user.has_capability('guest_meal.approve') and request.query_params.get('month'):
            qs = GuestMeal.objects.select_related('member', 'month').filter(month_id=request.query_params['month'])
        else:
            qs = GuestMeal.objects.select_related('member', 'month').filter(member=request.user)
        return Response(GuestMealSerializer(qs.order_by('meal_date'), many=True).data)

    def post(self, request):
        serializer = GuestMealSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            guest_meal = serializer.save()
            return Response(GuestMealSerializer(guest_meal).data, status=status.HTTP_201_CREATED)
        except NoMonthForDateError:
            return Response({'code': 'no_month_for_date'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise


class GuestMealApproveView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'guest_meal.approve'

    def post(self, request, pk):
        guest_meal = get_object_or_404(GuestMeal, pk=pk)
        if guest_meal.status != GuestMeal.Status.PENDING:
            return Response({'code': 'guest_meal_not_pending'}, status=status.HTTP_400_BAD_REQUEST)
        guest_meal.status = GuestMeal.Status.APPROVED
        guest_meal.processed_at = timezone.now()
        guest_meal.processed_by = request.user
        guest_meal.save(update_fields=['status', 'processed_at', 'processed_by'])
        return Response(GuestMealSerializer(guest_meal).data)


class GuestMealRejectView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)
    required_capability = 'guest_meal.approve'

    def post(self, request, pk):
        guest_meal = get_object_or_404(GuestMeal, pk=pk)
        reason = request.data.get('reason')
        if not reason:
            return Response({'code': 'reason_required'}, status=status.HTTP_400_BAD_REQUEST)
        if guest_meal.status != GuestMeal.Status.PENDING:
            return Response({'code': 'guest_meal_not_pending'}, status=status.HTTP_400_BAD_REQUEST)
        guest_meal.status = GuestMeal.Status.REJECTED
        guest_meal.rejection_reason = reason
        guest_meal.processed_at = timezone.now()
        guest_meal.processed_by = request.user
        guest_meal.save(update_fields=['status', 'rejection_reason', 'processed_at', 'processed_by'])
        return Response(GuestMealSerializer(guest_meal).data)
