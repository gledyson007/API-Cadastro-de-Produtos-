from rest_framework import serializers

class ProductSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    image_url = serializers.URLField(max_length=500)
    source = serializers.CharField(max_length=100, required=False, allow_null=True)
    unit = serializers.CharField(max_length=4)
    is_human_reviewed = serializers.BooleanField(read_only=True)
    data_source = serializers.CharField(read_only=True)