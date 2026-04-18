import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    resume_path = models.CharField(max_length=512, blank=True)
    resume_hash = models.CharField(max_length=64, blank=True)
    profile_json = models.JSONField(default=dict)
    persona = models.CharField(
        max_length=20,
        choices=[("Pivot", "Pivot"), ("Grow", "Grow"), ("Graduate", "Graduate")],
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.persona}"


class Session(models.Model):
    class Status(models.TextChoices):
        INTAKE = "INTAKE"
        PERSONA_DETECTED = "PERSONA_DETECTED"
        OPENING_SENT = "OPENING_SENT"
        GOAL_DISCOVERY = "GOAL_DISCOVERY"
        PATH_GEN = "PATH_GEN"
        PATH_PRESENTED = "PATH_PRESENTED"
        DEEP_DIVE = "DEEP_DIVE"
        CLOSED = "CLOSED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.INTAKE)
    current_round = models.IntegerField(default=0)
    workflow_id = models.CharField(max_length=256, blank=True)
    goal_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.id} [{self.status}]"


class ConversationTurn(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    class TurnType(models.TextChoices):
        OPENING = "opening"
        PATH_CARDS = "path_cards"
        FREE_TEXT = "free_text"
        OFF_TOPIC = "off_topic"
        FORCED_CLOSE = "forced_close"
        SYSTEM = "system"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="turns")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    turn_type = models.CharField(max_length=20, choices=TurnType.choices, default=TurnType.FREE_TEXT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class PathSet(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="path_sets")
    round_number = models.IntegerField()
    paths_json = models.JSONField(default=list)
    rejection_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["round_number"]


class SessionMetric(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="metrics")
    metric_name = models.CharField(max_length=100)
    metric_value = models.JSONField()
    recorded_at = models.DateTimeField(auto_now_add=True)


class Event(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="events", null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
