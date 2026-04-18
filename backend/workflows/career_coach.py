from datetime import timedelta
from dataclasses import dataclass, field
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.activities import (
        activity_extract_resume,
        activity_detect_persona,
        activity_generate_opening,
        activity_generate_paths,
    )


@dataclass
class GoalInput:
    alive_moments: list = field(default_factory=list)
    friction_points: list = field(default_factory=list)
    direction: str = "explore"
    geography: str = "India"
    aspiration: str = ""


@dataclass
class PathAction:
    action_type: str = "select"  # select | regenerate | free_text
    path_id: str = ""
    rejection_reason: str = ""
    message: str = ""


RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2))
ACTIVITY_OPTS = {"start_to_close_timeout": timedelta(minutes=5), "retry_policy": RETRY}


@workflow.defn
class CareerCoachWorkflow:
    def __init__(self):
        self._goal_input: GoalInput | None = None
        self._path_action: PathAction | None = None
        self._status = "INTAKE"
        self._opening: str = ""
        self._current_paths: list = []
        self._all_rejected_paths: list = []
        self._round = 0
        self._selected_path: dict | None = None

    @workflow.signal
    def goal_input(self, data: dict):
        self._goal_input = GoalInput(**data)

    @workflow.signal
    def path_action(self, data: dict):
        self._path_action = PathAction(**data)

    @workflow.query
    def get_status(self) -> str:
        return self._status

    @workflow.query
    def get_opening(self) -> str:
        return self._opening

    @workflow.query
    def get_current_paths(self) -> list:
        return self._current_paths

    @workflow.run
    async def run(self, session_id: str, resume_path: str) -> dict:
        self._status = "INTAKE"

        profile_dict = await workflow.execute_activity(
            activity_extract_resume, resume_path, **ACTIVITY_OPTS
        )

        persona_result = await workflow.execute_activity(
            activity_detect_persona, profile_dict, **ACTIVITY_OPTS
        )
        persona = persona_result["persona"]
        self._status = "PERSONA_DETECTED"

        opening = await workflow.execute_activity(
            activity_generate_opening, profile_dict, persona, **ACTIVITY_OPTS
        )
        self._opening = opening
        self._status = "OPENING_SENT"

        await workflow.wait_condition(lambda: self._goal_input is not None)
        goal = self._goal_input
        self._status = "PATH_GEN"

        self._round = 1
        paths = await workflow.execute_activity(
            activity_generate_paths,
            profile_dict, persona,
            goal.alive_moments, goal.friction_points,
            goal.direction, goal.geography,
            self._round, [], goal.aspiration,
            **ACTIVITY_OPTS,
        )
        self._current_paths = paths
        self._status = "PATH_PRESENTED"

        while self._round <= 3:
            self._path_action = None
            await workflow.wait_condition(lambda: self._path_action is not None)
            action = self._path_action

            if action.action_type == "select":
                self._selected_path = next(
                    (p for p in self._current_paths if p.get("id") == action.path_id),
                    self._current_paths[0] if self._current_paths else None,
                )
                self._status = "CLOSED"
                break

            elif action.action_type == "regenerate":
                self._all_rejected_paths.extend(self._current_paths)
                if self._round >= 3:
                    self._status = "CLOSED"
                    break
                self._round += 1
                self._status = "PATH_GEN"
                paths = await workflow.execute_activity(
                    activity_generate_paths,
                    profile_dict, persona,
                    goal.alive_moments, goal.friction_points,
                    goal.direction, goal.geography,
                    self._round, self._all_rejected_paths, goal.aspiration,
                    **ACTIVITY_OPTS,
                )
                self._current_paths = paths
                self._status = "PATH_PRESENTED"

            elif action.action_type == "free_text":
                self._status = "DEEP_DIVE"
                self._status = "PATH_PRESENTED"

        return {
            "session_id": session_id,
            "persona": persona,
            "selected_path": self._selected_path,
            "rounds_used": self._round,
        }
