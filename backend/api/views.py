import json
import hashlib
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Session, ConversationTurn, PathSet, UserProfile, Event, SessionMetric
from .serializers import (
    SignupSerializer, UserProfileSerializer, SessionSerializer, EventSerializer
)
from services import resume_parser
from services.agents import extractor, persona_detector, topic_classifier, conversation_router
from services.agents.opening_generator import generate_stream
from services.agents.extractor import ResumeProfile


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = SignupSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.id}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        profile = getattr(user, "profile", None)
        has_profile = bool(profile and profile.profile_json)
        return Response({
            "token": token.key,
            "user_id": user.id,
            "has_profile": has_profile,
        })


class ProfileUploadView(APIView):
    def post(self, request):
        resume_file = request.FILES.get("resume")
        if not resume_file:
            return Response({"error": "No resume file"}, status=status.HTTP_400_BAD_REQUEST)

        media_root = Path(settings.MEDIA_ROOT) / "resumes"
        media_root.mkdir(parents=True, exist_ok=True)
        safe_name = f"{request.user.id}_{resume_file.name}"
        save_path = media_root / safe_name

        with open(save_path, "wb") as f:
            for chunk in resume_file.chunks():
                f.write(chunk)

        file_hash = resume_parser.hash_file(str(save_path))
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)

        if profile_obj.resume_hash == file_hash and profile_obj.profile_json:
            return Response(UserProfileSerializer(profile_obj).data)

        try:
            text = resume_parser.extract_text(str(save_path))
            profile = extractor.extract(text)
            persona, _ = persona_detector.detect(profile)
        except Exception as e:
            return Response({"error": f"Resume parsing failed: {e}"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        profile_obj.resume_path = str(save_path)
        profile_obj.resume_hash = file_hash
        profile_obj.profile_json = profile.model_dump()
        profile_obj.persona = persona
        profile_obj.save()

        return Response(UserProfileSerializer(profile_obj).data)


class ProfileView(APIView):
    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "No profile found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserProfileSerializer(profile).data)


class SessionListView(APIView):
    def post(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({"error": "Upload a resume first"}, status=status.HTTP_400_BAD_REQUEST)

        if not profile.profile_json:
            return Response({"error": "Upload a resume first"}, status=status.HTTP_400_BAD_REQUEST)

        session = Session.objects.create(user=request.user, status=Session.Status.PERSONA_DETECTED)

        _record_event(request.user, session, "session_started", {})
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    def get(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id, user=request.user)
        except Session.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(SessionSerializer(session).data)


class SessionStreamView(APIView):
    def get(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id, user=request.user)
            profile = request.user.profile
        except (Session.DoesNotExist, UserProfile.DoesNotExist):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        resume_profile = ResumeProfile(**profile.profile_json)
        persona = profile.persona or "Grow"

        def _event_stream():
            full_response = []
            try:
                for token in generate_stream(resume_profile, persona):
                    full_response.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"
                complete_text = "".join(full_response)
                ConversationTurn.objects.create(
                    session=session,
                    role=ConversationTurn.Role.ASSISTANT,
                    content=complete_text,
                    turn_type=ConversationTurn.TurnType.OPENING,
                )
                session.status = Session.Status.OPENING_SENT
                session.save()
                yield f"data: {json.dumps({'done': True, 'turn_type': 'opening'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        response = StreamingHttpResponse(_event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class SessionGoalView(APIView):
    def post(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id, user=request.user)
            profile = request.user.profile
        except (Session.DoesNotExist, UserProfile.DoesNotExist):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        goal = {
            "alive_moments": request.data.get("alive_moments", []),
            "friction_points": request.data.get("friction_points", []),
            "direction": request.data.get("direction", "explore"),
            "geography": request.data.get("geography", "India"),
            "aspiration": request.data.get("aspiration", ""),
        }
        session.goal_json = goal
        session.status = Session.Status.PATH_GEN
        session.save()

        _record_event(request.user, session, "direction_selected", {"direction": goal["direction"]})

        resume_profile = ResumeProfile(**profile.profile_json)
        from services.agents.path_generator import generate as gen_paths

        try:
            cards = gen_paths(
                profile=resume_profile,
                persona=profile.persona or "Grow",
                alive_moments=goal["alive_moments"],
                friction_points=goal["friction_points"],
                direction=goal["direction"],
                geography=goal["geography"],
                round_number=1,
                rejected_paths=[],
                aspiration=goal["aspiration"],
            )
            paths_data = [c.model_dump() for c in cards]
        except Exception as e:
            return Response({"error": f"Path generation failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        path_set = PathSet.objects.create(session=session, round_number=1, paths_json=paths_data)
        session.status = Session.Status.PATH_PRESENTED
        session.current_round = 1
        session.save()

        return Response({"paths": paths_data, "round": 1})


class SessionMessageView(APIView):
    def post(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id, user=request.user)
            profile = request.user.profile
        except (Session.DoesNotExist, UserProfile.DoesNotExist):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        message = request.data.get("message", "").strip()
        if not message:
            return Response({"error": "Empty message"}, status=status.HTTP_400_BAD_REQUEST)

        ConversationTurn.objects.create(
            session=session, role=ConversationTurn.Role.USER, content=message
        )
        _record_event(request.user, session, "free_text_sent", {
            "length_bucket": "short" if len(message.split()) < 20 else "medium" if len(message.split()) < 100 else "long"
        })

        is_career, confidence = topic_classifier.classify(message)
        if not is_career and confidence >= 0.85:
            ConversationTurn.objects.create(
                session=session,
                role=ConversationTurn.Role.ASSISTANT,
                content=topic_classifier.OFF_TOPIC_REPLY,
                turn_type=ConversationTurn.TurnType.OFF_TOPIC,
            )
            return Response({"reply": topic_classifier.OFF_TOPIC_REPLY, "off_topic": True})

        resume_profile = ResumeProfile(**profile.profile_json)
        history = list(
            session.turns.filter(turn_type=ConversationTurn.TurnType.FREE_TEXT)
            .values("role", "content")
            .order_by("-created_at")[:10]
        )
        history = [{"role": t["role"], "content": t["content"]} for t in reversed(history)]

        intent, aspiration = conversation_router.classify_intent(message)

        def _stream():
            from services.agents.path_generator import generate as gen_paths
            full = []

            if intent == "path_request" and aspiration:
                stream_fn = conversation_router.respond_path_request(aspiration, resume_profile, message)
            else:
                stream_fn = conversation_router.respond_stream(message, resume_profile, history)

            for token in stream_fn:
                full.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

            reply = "".join(full)
            ConversationTurn.objects.create(
                session=session,
                role=ConversationTurn.Role.ASSISTANT,
                content=reply,
                turn_type=ConversationTurn.TurnType.FREE_TEXT,
            )

            done_payload = {"done": True, "intent": intent}

            if intent == "path_request" and aspiration:
                try:
                    # Reuse existing goal context if available, override aspiration
                    goal = session.goal_json or {}
                    new_round = session.current_round + 1 if session.current_round else 1
                    cards = gen_paths(
                        profile=resume_profile,
                        persona=profile.persona or "Grow",
                        alive_moments=goal.get("alive_moments", []),
                        friction_points=goal.get("friction_points", []),
                        direction=goal.get("direction", "explore"),
                        geography=goal.get("geography", "India"),
                        round_number=new_round,
                        rejected_paths=[],
                        aspiration=aspiration,
                    )
                    paths_data = [c.model_dump() for c in cards]
                    PathSet.objects.create(session=session, round_number=new_round, paths_json=paths_data)
                    session.current_round = new_round
                    session.status = Session.Status.PATH_PRESENTED
                    session.save()
                    done_payload["paths"] = paths_data
                    done_payload["round"] = new_round
                except Exception as e:
                    print(f"[path_request] path generation failed: {e}")

            yield f"data: {json.dumps(done_payload)}\n\n"

        resp = StreamingHttpResponse(_stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp


class SessionPathActionView(APIView):
    def post(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id, user=request.user)
            profile = request.user.profile
        except (Session.DoesNotExist, UserProfile.DoesNotExist):
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        action_type = request.data.get("type", "select")
        path_id = request.data.get("path_id", "")
        rejection_reason = request.data.get("reason", "")

        if action_type == "select":
            latest_set = session.path_sets.order_by("-round_number").first()
            selected = None
            if latest_set:
                for p in latest_set.paths_json:
                    if p.get("id") == path_id:
                        selected = p
                        break
            session.status = Session.Status.CLOSED
            session.closed_at = timezone.now()
            session.save()
            _record_event(request.user, session, "path_card_selected", {
                "round": session.current_round,
                "path_id": path_id,
            })
            _record_metric(session, "session_closed_happy", True)
            return Response({"selected_path": selected, "status": "CLOSED"})

        elif action_type == "regenerate":
            if session.current_round >= 3:
                latest_set = session.path_sets.order_by("-round_number").first()
                all_paths = []
                for ps in session.path_sets.all():
                    all_paths.extend(ps.paths_json)
                forced = all_paths[0] if all_paths else {}
                closing = (
                    f"Based on everything we've explored across {session.current_round} rounds, "
                    f"the best fit for your profile is: **{forced.get('role', 'the first path')}**. "
                    f"{forced.get('why_you_fit', '')} "
                    f"This is your strongest bridge given your background."
                )
                ConversationTurn.objects.create(
                    session=session,
                    role=ConversationTurn.Role.ASSISTANT,
                    content=closing,
                    turn_type=ConversationTurn.TurnType.FORCED_CLOSE,
                )
                session.status = Session.Status.CLOSED
                session.closed_at = timezone.now()
                session.save()
                _record_metric(session, "forced_close_rate", True)
                return Response({"forced_close": True, "message": closing, "status": "CLOSED"})

            resume_profile = ResumeProfile(**profile.profile_json)
            goal = session.goal_json
            all_rejected = []
            for ps in session.path_sets.all():
                all_rejected.extend(ps.paths_json)

            new_round = session.current_round + 1
            from services.agents.path_generator import generate as gen_paths
            try:
                cards = gen_paths(
                    profile=resume_profile,
                    persona=profile.persona or "Grow",
                    alive_moments=goal.get("alive_moments", []),
                    friction_points=goal.get("friction_points", []),
                    direction=goal.get("direction", "explore"),
                    geography=goal.get("geography", "India"),
                    round_number=new_round,
                    rejected_paths=all_rejected,
                    aspiration=goal.get("aspiration", ""),
                )
                paths_data = [c.model_dump() for c in cards]
            except Exception as e:
                return Response({"error": f"Regeneration failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            PathSet.objects.create(
                session=session,
                round_number=new_round,
                paths_json=paths_data,
                rejection_reason=rejection_reason,
            )
            session.current_round = new_round
            session.status = Session.Status.PATH_PRESENTED
            session.save()

            _record_event(request.user, session, "path_regenerated", {
                "round": new_round,
                "rejection_reason": rejection_reason,
            })
            return Response({"paths": paths_data, "round": new_round})

        return Response({"error": "Unknown action type"}, status=status.HTTP_400_BAD_REQUEST)


class EventIngestView(APIView):
    def post(self, request):
        events = request.data if isinstance(request.data, list) else [request.data]
        for evt in events:
            session_id = evt.pop("session_id", None)
            session = None
            if session_id:
                try:
                    session = Session.objects.get(id=session_id, user=request.user)
                except Session.DoesNotExist:
                    pass
            Event.objects.create(
                user=request.user,
                session=session,
                event_type=evt.get("event_type", "unknown"),
                payload=evt.get("payload", {}),
            )
        return Response({"status": "ok"})


class MetricsSummaryView(APIView):
    def get(self, request):
        from django.db.models import Count, Avg, Q
        from django.db.models.functions import TruncDate

        sessions = Session.objects.filter(user=request.user)
        total = sessions.count()

        funnel = {
            "started": total,
            "goal_discovered": sessions.exclude(goal_json={}).count(),
            "paths_seen": sessions.filter(status__in=["PATH_PRESENTED", "DEEP_DIVE", "CLOSED"]).count(),
            "path_selected": sessions.filter(status="CLOSED").count(),
        }

        persona_breakdown = dict(
            UserProfile.objects.filter(user=request.user).values("persona").annotate(c=Count("id")).values_list("persona", "c")
        )

        event_counts = dict(
            Event.objects.filter(user=request.user)
            .values("event_type")
            .annotate(c=Count("id"))
            .values_list("event_type", "c")
        )

        regen_events = Event.objects.filter(user=request.user, event_type="path_regenerated")
        rejection_reasons = {}
        for e in regen_events:
            r = e.payload.get("rejection_reason", "unspecified")
            rejection_reasons[r] = rejection_reasons.get(r, 0) + 1

        return Response({
            "funnel": funnel,
            "persona_breakdown": persona_breakdown,
            "event_counts": event_counts,
            "rejection_reasons": rejection_reasons,
            "total_sessions": total,
        })


def _record_event(user, session, event_type, payload):
    Event.objects.create(user=user, session=session, event_type=event_type, payload=payload)


def _record_metric(session, name, value):
    SessionMetric.objects.create(session=session, metric_name=name, metric_value=value)
