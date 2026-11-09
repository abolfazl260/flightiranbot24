"""The trusted local moderation workflow exposes enough context to review safely."""

import json
import os
import subprocess
import sys

import pytest

from flightiran.db import initialize_database
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.modules.experiences.persistent import SQLiteExperienceService


@pytest.mark.asyncio
async def test_cli_queue_detail_and_moderation_preserve_full_user_content(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'moderation.db'}"
    db = await initialize_database(url)
    user = await SQLiteUserRepository(db).create(101)
    result = await SQLiteExperienceService(db).submit(
        user.id, targets=["airport:IKA"], body="A complete real travel experience for review.",
        rating=4, criteria={"cleanliness": 5}, consent=True, display_name="Anonymous",
    )
    await db.close()
    env = {**os.environ, "DATABASE_URL": url}

    def run(*args):
        return subprocess.run(
            [sys.executable, "scripts/manage_experiences.py", *args],
            env=env, check=True, capture_output=True, text=True,
        ).stdout

    queue = json.loads(run("queue", "--kind", "user"))
    assert queue["items"][0]["targets"] == ["airport:IKA"]
    assert queue["items"][0]["rating"] == 4
    assert queue["items"][0]["criteria"] == {"cleanliness": 5}
    assert queue["next_offset"] is None
    identifier = str(result["id"])
    detail = json.loads(run("show", "--id", identifier))
    assert detail["body"] == "A complete real travel experience for review."
    assert detail["state"] == "pending" and detail["public_text"] is None
    run("moderate", "--id", identifier, "--state", "approved",
        "--operator", "test-reviewer", "--reason", "Reviewed owner consent and content")
    detail = json.loads(run("show", "--id", identifier))
    assert detail["state"] == "approved" and detail["public_text"] == detail["body"]
