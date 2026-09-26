from django.db import transaction
from rest_framework import serializers

from apps.guest_meals.models import GuestMeal
from apps.months.models import Month
from apps.months.utils import NoMonthForDateError, is_meal_submission_deadline_passed, resolve_month_for_date


class GuestMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestMeal
        fields = (
            'id', 'member', 'month', 'meal_date', 'lunch_quantity', 'dinner_quantity',
            'status', 'rejection_reason', 'remarks', 'submitted_at', 'processed_at', 'processed_by'
        )
        read_only_fields = ('id', 'member', 'month', 'status', 'rejection_reason', 'submitted_at', 'processed_at', 'processed_by')

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

        lunch_qty = attrs.get('lunch_quantity', 0)
        dinner_qty = attrs.get('dinner_quantity', 0)
        if lunch_qty <= 0 and dinner_qty <= 0:
            raise serializers.ValidationError({'detail': 'At least one quantity must be greater than zero.'})

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

            existing = GuestMeal.objects.filter(member=request.user, meal_date=meal_date).exclude(status=GuestMeal.Status.REJECTED).order_by('-submitted_at').first()
            if existing is not None:
                if existing.status == GuestMeal.Status.APPROVED:
                    raise serializers.ValidationError({'code': 'already_approved'})
                existing.month = month
                existing.lunch_quantity = validated_data.get('lunch_quantity', existing.lunch_quantity)
                existing.dinner_quantity = validated_data.get('dinner_quantity', existing.dinner_quantity)
                existing.remarks = validated_data.get('remarks', existing.remarks)
                existing.status = GuestMeal.Status.PENDING
                existing.rejection_reason = ''
                existing.processed_at = None
                existing.processed_by = None
                existing.save()
                return existing

            guest_meal = GuestMeal.objects.create(
                member=request.user,
                month=month,
                meal_date=meal_date,
                lunch_quantity=validated_data.get('lunch_quantity', 0),
                dinner_quantity=validated_data.get('dinner_quantity', 0),
                remarks=validated_data.get('remarks', ''),
                status=GuestMeal.Status.PENDING,
            )
            return guest_meal
