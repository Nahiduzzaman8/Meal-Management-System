from rest_framework import serializers

from apps.months.models import MonthMember


class MonthReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthMember
        fields = (
            'id', 'member', 'opening_balance', 'lunch_count', 'dinner_count', 'meal_units',
            'guest_lunch_count', 'guest_dinner_count', 'guest_meal_units', 'meal_rate_applied',
            'meal_cost', 'guest_meal_cost', 'adjustment_total', 'total_cost', 'approved_deposit_total',
            'closing_balance', 'finalized_at'
        )


class BalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthMember
        fields = ('month', 'closing_balance', 'finalized_at')
