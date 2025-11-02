# myapp/serializers.py
from rest_framework import serializers
from .models import Video
from bson import ObjectId

class VideotSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    def get_id(self, obj):
        return str(obj.id)  # Convert ObjectId to string

    class Meta:
        model = Video
        fields = ['id', 'name', 'description', 'price', 'created_at']


# myapp/serializers.py
from rest_framework import serializers

class PresignedUrlRequestSerializer(serializers.Serializer):
    filename = serializers.CharField()
    filetype = serializers.CharField()
    filesize = serializers.IntegerField()
