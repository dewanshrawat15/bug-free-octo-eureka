from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, Session, ConversationTurn, PathSet, Event


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    name = serializers.CharField(max_length=100)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("name", "").split()[0],
            last_name=" ".join(validated_data.get("name", "").split()[1:]),
        )
        UserProfile.objects.create(user=user)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["email", "name", "persona", "profile_json", "updated_at"]

    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class ConversationTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationTurn
        fields = ["id", "role", "content", "turn_type", "created_at"]


class PathSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PathSet
        fields = ["id", "round_number", "paths_json", "rejection_reason", "created_at"]


class SessionSerializer(serializers.ModelSerializer):
    turns = ConversationTurnSerializer(many=True, read_only=True)
    path_sets = PathSetSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = ["id", "status", "current_round", "goal_json", "created_at", "turns", "path_sets"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["event_type", "payload", "timestamp"]
