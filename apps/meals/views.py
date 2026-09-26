from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.meals.models import Meal
from apps.meals.serializers import MealSerializer
from apps.months.models import Month
from apps.months.utils import NoMonthForDateError, resolve_month_for_date
from apps.users.permissions import HasCapability


class MealListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasCapability)

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            self.required_capability = 'meal.view_all' if request.user.has_capability('meal.view_all') and request.query_params.get('month') else 'meal.view_own'
        elif request.method == 'POST':
            self.required_capability = 'meal.submit'
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.user.has_capability('meal.view_all') and request.query_params.get('month'):
            qs = Meal.objects.select_related('member', 'month').filter(month_id=request.query_params['month'])
        else:
            qs = Meal.objects.select_related('member', 'month').filter(member=request.user)
        return Response(MealSerializer(qs.order_by('meal_date'), many=True).data)

    def post(self, request):
        serializer = MealSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            meal = serializer.save()
            return Response(MealSerializer(meal).data, status=status.HTTP_201_CREATED)
        except NoMonthForDateError:
            return Response({'code': 'no_month_for_date'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            detail = getattr(exc, 'detail', None)
            if isinstance(detail, dict) and 'code' in detail:
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise
