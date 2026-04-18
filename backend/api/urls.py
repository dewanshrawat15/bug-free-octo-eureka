from django.urls import path
from . import views

urlpatterns = [
    path("auth/signup/", views.SignupView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("profile/", views.ProfileView.as_view()),
    path("profile/upload/", views.ProfileUploadView.as_view()),
    path("sessions/", views.SessionListView.as_view()),
    path("sessions/<uuid:session_id>/", views.SessionDetailView.as_view()),
    path("sessions/<uuid:session_id>/stream/", views.SessionStreamView.as_view()),
    path("sessions/<uuid:session_id>/goal/", views.SessionGoalView.as_view()),
    path("sessions/<uuid:session_id>/message/", views.SessionMessageView.as_view()),
    path("sessions/<uuid:session_id>/path-action/", views.SessionPathActionView.as_view()),
    path("events/", views.EventIngestView.as_view()),
    path("metrics/summary/", views.MetricsSummaryView.as_view()),
]
