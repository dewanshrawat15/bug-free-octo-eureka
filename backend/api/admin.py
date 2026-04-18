from django.contrib import admin
from .models import UserProfile, Session, ConversationTurn, PathSet, SessionMetric, Event

admin.site.register(UserProfile)
admin.site.register(Session)
admin.site.register(ConversationTurn)
admin.site.register(PathSet)
admin.site.register(SessionMetric)
admin.site.register(Event)
