from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.months.models import Month, MonthMember
from apps.months.utils import estimate_open_month_rate
from apps.users.models import User


class MonthlyReportView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        month_id = request.query_params.get('month_id')
        if not month_id:
            return Response({'detail': 'month_id is required'}, status=400)

        month = get_object_or_404(Month, pk=month_id)
        if request.user.has_capability('report.view_all') or request.user == month.created_by:
            members = MonthMember.objects.filter(month=month).order_by('member_id')
        else:
            members = MonthMember.objects.filter(month=month, member=request.user)

        rate_status = 'FINAL' if month.status == Month.Status.CLOSED else 'ESTIMATED'
        estimated_rate = estimate_open_month_rate(month) if month.status != Month.Status.CLOSED else month.final_meal_rate
        payload = {
            'month': {'id': month.id, 'name': month.name, 'status': month.status},
            'rate_status': rate_status,
            'estimated_meal_rate': estimated_rate,
            'final_meal_rate': month.final_meal_rate,
            'final_total_expense': month.final_total_expense,
            'rounding_residual': month.rounding_residual,
            'members': [
                {
                    'member_id': mm.member_id,
                    'username': mm.member.username,
                    'meal_units': mm.meal_units,
                    'guest_meal_units': mm.guest_meal_units,
                    'total_cost': mm.total_cost,
                    'closing_balance': mm.closing_balance,
                }
                for mm in members
            ],
        }
        return Response(payload)


class MembersReportView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        month_id = request.query_params.get('month_id')
        if not month_id:
            return Response({'detail': 'month_id is required'}, status=400)

        month = get_object_or_404(Month, pk=month_id)
        if request.user.has_capability('report.view_all'):
            qs = MonthMember.objects.filter(month=month).order_by('member_id')
        else:
            qs = MonthMember.objects.filter(month=month, member=request.user)
        return Response([
            {
                'member_id': mm.member_id,
                'username': mm.member.username,
                'opening_balance': mm.opening_balance,
                'meal_units': mm.meal_units,
                'guest_meal_units': mm.guest_meal_units,
                'closing_balance': mm.closing_balance,
                'finalized_at': mm.finalized_at,
            }
            for mm in qs
        ])


class BalancesReportView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        member_id = request.query_params.get('member_id')
        if not member_id:
            return Response({'detail': 'member_id is required'}, status=400)

        member = get_object_or_404(User, pk=member_id)
        if member_id != str(request.user.id) and not request.user.has_capability('report.view_all'):
            return Response({'detail': 'Forbidden'}, status=403)

        qs = MonthMember.objects.filter(member=member, finalized_at__isnull=False).order_by('finalized_at')
        return Response([
            {
                'month_id': mm.month_id,
                'month_name': mm.month.name,
                'closing_balance': mm.closing_balance,
                'finalized_at': mm.finalized_at,
            }
            for mm in qs
        ])
