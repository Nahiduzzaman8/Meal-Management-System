from django.db import transaction
from rest_framework import serializers

from apps.expenses.models import Expense
from apps.months.models import Month


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = (
            'id', 'month', 'created_by', 'category', 'amount', 'expense_date',
            'description', 'is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'
        )
        read_only_fields = ('id', 'month', 'created_by', 'is_deleted', 'deleted_at', 'deleted_by', 'delete_reason')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('amount must be greater than zero')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        month = attrs.get('month')
        if month is None:
            month = Month.objects.filter(status=Month.Status.OPEN).order_by('-start_date').first()
            if month is None:
                raise serializers.ValidationError({'code': 'no_open_month'})
            attrs['month'] = month

        expense_date = attrs.get('expense_date')
        description = attrs.get('description', '').strip()

        if not description:
            raise serializers.ValidationError({'description': 'This field is required.'})

        if month.status != Month.Status.OPEN:
            raise serializers.ValidationError({'code': 'month_not_open'})
        if expense_date is None:
            raise serializers.ValidationError({'expense_date': 'This field is required.'})
        if not (month.start_date <= expense_date <= month.end_date):
            raise serializers.ValidationError({'expense_date': 'Expense date must be within the month.'})

        attrs['created_by'] = request.user
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            month = Month.objects.select_for_update().get(pk=validated_data['month'].pk)
            if month.status != Month.Status.OPEN:
                raise serializers.ValidationError({'code': 'month_not_open'})
            return Expense.objects.create(**validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            month = instance.month
            month = Month.objects.select_for_update().get(pk=month.pk)
            if month.status != Month.Status.OPEN:
                raise serializers.ValidationError({'code': 'month_not_open'})
            if 'expense_date' in validated_data and validated_data['expense_date'] is not None:
                expense_date = validated_data['expense_date']
                if not (month.start_date <= expense_date <= month.end_date):
                    raise serializers.ValidationError({'expense_date': 'Expense date must be within the month.'})
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
