from rest_framework import serializers
from apps.months.models import Month, MonthMember


class MonthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Month
        fields = ('id', 'name', 'start_date', 'end_date', 'status', 'final_meal_rate', 'final_total_expense', 'rounding_residual')


class MonthMemberSerializer(serializers.ModelSerializer):
    member_username = serializers.CharField(source='member.username', read_only=True)

    class Meta:
        model = MonthMember
        fields = ('id', 'member', 'member_username', 'joined_on', 'left_on', 'opening_balance', 'lunch_count', 'dinner_count', 'meal_units', 'guest_lunch_count', 'guest_dinner_count', 'guest_meal_units', 'meal_rate_applied', 'meal_cost', 'guest_meal_cost', 'adjustment_total', 'total_cost', 'approved_deposit_total', 'closing_balance', 'finalized_at')
