import uuid

from rest_framework import serializers

from dashboard.models import Share


class ShareSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "isin",
            "name",
            "ticker",
            "currency",
            "uid",
            "last_price",
            "is_trend_high",
            "updated_at",
        )

    def create(self, validated_data):
        validated_data.setdefault("uid", str(uuid.uuid4()))
        return super().create(validated_data)
