from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.deposits.models import Deposit
from apps.months.models import Month


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = (
            'id', 'member', 'month', 'amount', 'payment_method', 'transaction_reference',
            'payment_date', 'status', 'rejection_reason', 'submitted_at', 'processed_at', 'processed_by'
        )
        read_only_fields = ('id', 'member', 'month', 'status', 'rejection_reason', 'submitted_at', 'processed_at', 'processed_by')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('amount must be greater than zero')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        payment_method = attrs.get('payment_method')
        transaction_reference = attrs.get('transaction_reference', '')

        if payment_method != Deposit.PaymentMethod.CASH and not transaction_reference.strip():
            raise serializers.ValidationError({'transaction_reference': 'This field is required for non-cash payments.'})

        payment_date = attrs.get('payment_date')
        if payment_date is None:
            raise serializers.ValidationError({'payment_date': 'This field is required.'})

        open_month = Month.objects.filter(status=Month.Status.OPEN).order_by('-start_date').first()
        if open_month is None:
            raise serializers.ValidationError({'code': 'month_not_open'})

        attrs['month'] = open_month
        attrs['member'] = request.user
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            month = Month.objects.select_for_update().get(pk=validated_data['month'].pk)
            if month.status != Month.Status.OPEN:
                raise serializers.ValidationError({'code': 'month_not_open'})
            return Deposit.objects.create(**validated_data)
