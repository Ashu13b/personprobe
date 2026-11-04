import json
from pathlib import Path

import pytest

from engine.agent_llm import AgentProvider, pending_jobs
from scripts.agent_jobs_worker import (
    check_claim_grounding,
    do_answer,
    do_list,
    do_prune,
    guess_job_kind,
    main,
    validate_answer,
)


@pytest.fixture
def test_jobs_dir(tmp_path: Path) -> Path:
    jobs_dir = tmp_path / "agent_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def test_guess_job_kind():
    assert guess_job_kind("Extract structured facts about a person") == "extraction"
    assert (
        guess_job_kind("You are a Wikipedia source reliability classifier")
        == "classification"
    )
    assert (
        guess_job_kind("Generate 6 targeted web search queries")
        == "query_generation"
    )
    assert guess_job_kind("Unknown system instruction") == "other"


def test_check_claim_grounding():
    content = "Dr. Vishwa Mohan Katoch served as Director-General of ICMR."
    # Grounded claim
    is_grounded, ratio, missing = check_claim_grounding(
        "Director-General of ICMR", content
    )
    assert is_grounded
    assert ratio >= 0.5
    assert len(missing) == 0

    # Fabricated claim
    is_grounded, ratio, missing = check_claim_grounding(
        "Awarded Nobel Prize in Physiology in Stockholm", content
    )
    assert not is_grounded
    assert ratio < 0.5
    assert "nobel" in missing
    assert "stockholm" in missing


def test_validate_answer_extraction(test_jobs_dir: Path):
    job = {
        "id": "job123",
        "system": "Extract structured facts about a person from a source for a Wikipedia article.",
        "user": "Person: Test Person\nContent: Test Person is a Professor of Biology at Harvard University.",
    }

    # Valid grounded answer
    valid_ans = json.dumps(
        {
            "claims": [
                {
                    "field": "affiliation",
                    "text": "Professor of Biology at Harvard University",
                }
            ]
        }
    )
    parsed = validate_answer(job, valid_ans)
    assert len(parsed["claims"]) == 1

    # Invalid JSON
    with pytest.raises(ValueError, match="not valid JSON"):
        validate_answer(job, "{not-json}")

    # Missing claims list
    with pytest.raises(ValueError, match="must contain a 'claims' list"):
        validate_answer(job, json.dumps({"facts": []}))

    # Invalid field
    with pytest.raises(ValueError, match="invalid field 'invented_field'"):
        validate_answer(
            job,
            json.dumps(
                {
                    "claims": [
                        {
                            "field": "invented_field",
                            "text": "Professor of Biology at Harvard University",
                        }
                    ]
                }
            ),
        )

    # Fabricated / ungrounded claim text
    with pytest.raises(ValueError, match="failed grounding check"):
        validate_answer(
            job,
            json.dumps(
                {
                    "claims": [
                        {
                            "field": "award",
                            "text": "Conferred the prestigious Bharat Ratna award in New Delhi",
                        }
                    ]
                }
            ),
        )


def test_validate_answer_classification():
    job = {
        "id": "job_class",
        "system": "You are a Wikipedia source reliability classifier following WP:RS policy.",
        "user": "URL: https://example.com",
    }

    valid_ans = json.dumps(
        {
            "reliability": "reliable_secondary",
            "reason": "Independent reporting from major news outlet.",
        }
    )
    parsed = validate_answer(job, valid_ans)
    assert parsed["reliability"] == "reliable_secondary"

    # Invalid reliability
    with pytest.raises(ValueError, match="Invalid reliability 'super_reliable'"):
        validate_answer(job, json.dumps({"reliability": "super_reliable"}))


def test_worker_roundtrip_with_agent_provider(test_jobs_dir: Path):
    provider = AgentProvider(jobs_dir=test_jobs_dir)
    system = "Extract structured facts about a person from a source for a Wikipedia article."
    user = (
        "Person: Vishwa Mohan Katoch\n"
        "Source URL: https://icmr.gov.in\n"
        "Content: Former Director-General of the Indian Council of Medical Research."
    )

    # Initial call queues the job and returns "{}"
    res = provider.complete(system, user)
    assert res == "{}"

    pending = pending_jobs(test_jobs_dir)
    assert len(pending) == 1
    job_id = pending[0]["id"]

    # Worker list surfaces it
    items = do_list(test_jobs_dir)
    assert len(items) == 1
    assert items[0]["id"] == job_id
    assert items[0]["kind"] == "extraction"
    assert items[0]["url"] == "https://icmr.gov.in"

    # Worker answers the job
    ans_payload = json.dumps(
        {
            "claims": [
                {
                    "field": "position",
                    "text": "Former Director-General of the Indian Council of Medical Research",
                }
            ]
        }
    )
    do_answer(job_id, ans_payload, test_jobs_dir)

    # Re-run prompt through AgentProvider returns the answer
    res_rerun = provider.complete(system, user)
    assert "Former Director-General" in res_rerun

    # Pending jobs is now empty
    assert len(pending_jobs(test_jobs_dir)) == 0


def test_worker_prune_unanswered_jobs(test_jobs_dir: Path):
    import time

    # Create an old unanswered job
    old_job = test_jobs_dir / "old123.job.json"
    old_job.write_text(
        json.dumps({"id": "old123", "system": "test", "user": "test"})
    )
    # Set mtime to 10 days ago
    ten_days_ago = time.time() - (10 * 86400)
    import os

    os.utime(old_job, (ten_days_ago, ten_days_ago))

    # Create an old ANSWERED job
    old_answered_job = test_jobs_dir / "old_ans.job.json"
    old_answered_job.write_text(
        json.dumps({"id": "old_ans", "system": "test", "user": "test"})
    )
    old_resp = test_jobs_dir / "old_ans.response.json"
    old_resp.write_text(json.dumps({"id": "old_ans", "response": "{}"}))
    os.utime(old_answered_job, (ten_days_ago, ten_days_ago))
    os.utime(old_resp, (ten_days_ago, ten_days_ago))

    # Create a fresh unanswered job (today)
    fresh_job = test_jobs_dir / "fresh123.job.json"
    fresh_job.write_text(
        json.dumps({"id": "fresh123", "system": "test", "user": "test"})
    )

    # Prune older than 7 days
    pruned = do_prune(older_than_days=7, jobs_dir=test_jobs_dir)
    assert pruned == 1

    # Old unanswered is deleted
    assert not old_job.exists()
    # Old answered is PRESERVED
    assert old_answered_job.exists()
    assert old_resp.exists()
    # Fresh unanswered is PRESERVED
    assert fresh_job.exists()


def test_worker_cli_main(tmp_path: Path):
    jobs_dir = tmp_path / "agent_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / "test1.job.json"
    job_file.write_text(
        json.dumps(
            {
                "id": "test1",
                "system": "Extract structured facts about a person from a source for a Wikipedia article.",
                "user": "Person: Alice\nContent: Alice is a researcher at Stanford University.",
            }
        )
    )

    # Test CLI list
    ret = main(["list", "--repo", str(tmp_path)])
    assert ret == 0

    # Test CLI answer with valid json
    ans = json.dumps(
        {
            "claims": [
                {
                    "field": "affiliation",
                    "text": "Researcher at Stanford University",
                }
            ]
        }
    )
    ret = main(["answer", "--repo", str(tmp_path), "--job", "test1", "--json", ans])
    assert ret == 0
    assert (jobs_dir / "test1.response.json").exists()

    # Test CLI answer with ungrounded text fails with error code 1
    ungrounded_ans = json.dumps(
        {
            "claims": [
                {
                    "field": "award",
                    "text": "Won Olympic Gold Medal in Tokyo",
                }
            ]
        }
    )
    ret = main(
        [
            "answer",
            "--repo",
            str(tmp_path),
            "--job",
            "test1",
            "--json",
            ungrounded_ans,
        ]
    )
    assert ret == 1
