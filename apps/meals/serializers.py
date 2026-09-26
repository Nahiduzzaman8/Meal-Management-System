from django.db import transaction
from rest_framework import serializers

from apps.meals.models import Meal
from apps.months.models import Month
from apps.months.utils import NoMonthForDateError, is_meal_submission_deadline_passed, resolve_month_for_date


class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ('id', 'member', 'month', 'meal_date', 'lunch', 'dinner', 'created_at', 'updated_at')
        read_only_fields = ('id', 'member', 'month', 'created_at', 'updated_at')

    def validate(self, attrs):
        meal_date = attrs.get('meal_date')
        if meal_date is None:
            raise serializers.ValidationError({'meal_date': 'This field is required.'})

        try:
            month = resolve_month_for_date(meal_date)
        except NoMonthForDateError:
            raise serializers.ValidationError({'code': 'no_month_for_date'})

        if month.status == Month.Status.CLOSED:
            raise serializers.ValidationError({'code': 'no_month_for_date'})

        if is_meal_submission_deadline_passed(meal_date):
            raise serializers.ValidationError({'code': 'deadline_passed'})

        attrs['month'] = month
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        meal_date = validated_data['meal_date']
        month = validated_data['month']

        with transaction.atomic():
            month = Month.objects.select_for_update().get(pk=month.pk)
            if month.status == Month.Status.CLOSED:
                raise serializers.ValidationError({'code': 'no_month_for_date'})

            meal, _ = Meal.objects.get_or_create(
                member=request.user,
                meal_date=meal_date,
                defaults={'month': month, 'lunch': validated_data.get('lunch', False), 'dinner': validated_data.get('dinner', False)},
            )
            if not meal._state.adding:
                meal.month = month
                meal.lunch = validated_data.get('lunch', meal.lunch)
                meal.dinner = validated_data.get('dinner', meal.dinner)
                meal.save(update_fields=['month', 'lunch', 'dinner', 'updated_at'])
            return meal
