from rest_framework import serializers

from apps.adjustments.models import Adjustment
from apps.months.models import Month


class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = (
            'id', 'month', 'member', 'direction', 'amount', 'reason',
            'source_entity_type', 'source_entity_id', 'created_by', 'created_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('amount must be greater than zero')
        return value

    def validate(self, attrs):
        month = attrs.get('month')
        reason = attrs.get('reason', '').strip()
        if not reason:
            raise serializers.ValidationError({'reason': 'This field is required.'})
        if month is None:
            raise serializers.ValidationError({'month': 'This field is required.'})
        if month.status != Month.Status.OPEN:
            raise serializers.ValidationError({'code': 'month_not_open'})
        attrs['created_by'] = self.context['request'].user
        return attrs
