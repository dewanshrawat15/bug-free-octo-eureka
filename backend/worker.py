#!/usr/bin/env python
import asyncio
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from temporalio.client import Client
from temporalio.worker import Worker
from workflows.career_coach import CareerCoachWorkflow
from workflows.activities import (
    activity_extract_resume,
    activity_detect_persona,
    activity_generate_opening,
    activity_generate_paths,
)


async def main():
    import asyncio as _asyncio

    for attempt in range(15):
        try:
            client = await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)
            break
        except Exception as e:
            print(f"Temporal not ready (attempt {attempt + 1}/15): {e}")
            await _asyncio.sleep(5)
    else:
        raise RuntimeError("Could not connect to Temporal after 15 attempts")

    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[CareerCoachWorkflow],
        activities=[
            activity_extract_resume,
            activity_detect_persona,
            activity_generate_opening,
            activity_generate_paths,
        ],
    )
    print(f"Worker started on task queue: {settings.TEMPORAL_TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
