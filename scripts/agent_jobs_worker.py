#!/usr/bin/env python3
"""Worker CLI for the agent_jobs queue.

Usage:
    scripts/agent_jobs_worker.py list [--repo PATH] [--limit N]
    scripts/agent_jobs_worker.py answer --job <id> --json <file-or-inline> [--repo PATH]
    scripts/agent_jobs_worker.py prune [--older-than-days N] [--repo PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Ensure root dir is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.agent_llm import answer_job, pending_jobs  # noqa: E402

VALID_EXTRACTION_FIELDS: frozenset[str] = frozenset(
    [
        "full_name",
        "birth_date",
        "birth_place",
        "death_date",
        "nationality",
        "field",
        "affiliation",
        "education",
        "position",
        "known_for",
        "award",
        "publication",
    ]
)

VALID_RELIABILITY_VALUES: frozenset[str] = frozenset(
    [
        "reliable_secondary",
        "primary",
        "self_published",
        "unreliable",
    ]
)

STOPWORDS: frozenset[str] = frozenset(
    [
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "also",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "with",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    ]
)


def guess_job_kind(system_text: str) -> str:
    """Classify job kind from the system prompt."""
    s = system_text.lower()
    if "extract structured facts" in s:
        return "extraction"
    if "source reliability classifier" in s or "wp:rs" in s:
        return "classification"
    if "search queries" in s or "research assistant" in s:
        return "query_generation"
    return "other"


def extract_url(user_text: str) -> str | None:
    m = re.search(r"(?:Source URL|URL):\s*([^\n]+)", user_text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_person(user_text: str) -> str | None:
    m = re.search(r"Person:\s*([^\n]+)", user_text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_content(user_text: str) -> str:
    m = re.search(
        r"(?:Content|Snippet):\s*(.*?)(?=\n[A-Z][a-zA-Z0-9_\s]*:|\Z)",
        user_text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return user_text.strip()


def extract_key_tokens(text: str) -> list[str]:
    """Tokenize and remove stopwords and short punctuation-only tokens."""
    raw_tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in raw_tokens if len(t) > 2 and t not in STOPWORDS]


def check_claim_grounding(
    claim_text: str, context_text: str, threshold: float = 0.5
) -> tuple[bool, float, list[str]]:
    """Verify that key tokens in claim_text are grounded in context_text.

    Returns (is_grounded, match_ratio, missing_tokens).
    """
    claim_tokens = extract_key_tokens(claim_text)
    if not claim_tokens:
        return True, 1.0, []

    context_tokens = set(extract_key_tokens(context_text))
    matched = [t for t in claim_tokens if t in context_tokens]
    missing = [t for t in claim_tokens if t not in context_tokens]
    ratio = len(matched) / len(claim_tokens)
    return ratio >= threshold, ratio, missing


def validate_answer(job_dict: dict[str, Any], answer_json_str: str) -> dict[str, Any]:
    """Validate an answer against the job prompt and schema requirements.

    Raises ValueError if validation fails.
    Returns parsed answer dict.
    """
    try:
        parsed = json.loads(answer_json_str)
    except Exception as exc:
        raise ValueError(f"Answer is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Answer JSON must be an object/dict")

    system_text = job_dict.get("system", "")
    user_text = job_dict.get("user", "")
    kind = guess_job_kind(system_text)

    if kind == "extraction":
        claims = parsed.get("claims")
        if not isinstance(claims, list):
            raise ValueError(
                "Extraction answer must contain a 'claims' list: {'claims': [...]}"
            )

        person = extract_person(user_text) or ""
        content = extract_content(user_text)
        context_text = f"{person}\n{content}"

        for i, c in enumerate(claims):
            if not isinstance(c, dict):
                raise ValueError(f"Claim #{i} must be a dict object")
            field = c.get("field")
            text = c.get("text")
            if not field or not isinstance(field, str):
                raise ValueError(f"Claim #{i} missing valid 'field' string")
            if field not in VALID_EXTRACTION_FIELDS:
                raise ValueError(
                    f"Claim #{i} invalid field '{field}'. Must be one of {sorted(VALID_EXTRACTION_FIELDS)}"
                )
            if not text or not isinstance(text, str) or not text.strip():
                raise ValueError(f"Claim #{i} missing non-empty 'text' string")

            # Grounding check: verify against provided user content
            is_grounded, ratio, missing = check_claim_grounding(text, context_text)
            if not is_grounded:
                raise ValueError(
                    f"Claim #{i} failed grounding check (match ratio {ratio:.2f} < 0.50): "
                    f"text {text!r} has unsupported key tokens {missing[:5]}"
                )

            date_context = c.get("date_context")
            if date_context is not None:
                if not isinstance(date_context, str) or not date_context.strip():
                    raise ValueError(
                        f"Claim #{i} 'date_context' must be a non-empty string if provided"
                    )
                is_d_grounded, _, missing_d = check_claim_grounding(
                    date_context, context_text
                )
                if not is_d_grounded:
                    raise ValueError(
                        f"Claim #{i} date_context {date_context!r} not supported by source content: missing {missing_d}"
                    )

    elif kind == "classification":
        rel = parsed.get("reliability")
        if not rel or not isinstance(rel, str):
            raise ValueError("Classification answer must contain 'reliability' string")
        if rel not in VALID_RELIABILITY_VALUES:
            raise ValueError(
                f"Invalid reliability '{rel}'. Must be one of {sorted(VALID_RELIABILITY_VALUES)}"
            )

    return parsed


def do_list(jobs_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """List pending jobs with summary metadata, sorted newest first."""
    pending = pending_jobs(jobs_dir)

    def _mtime(j: dict[str, Any]) -> float:
        try:
            return (jobs_dir / f"{j['id']}.job.json").stat().st_mtime
        except Exception:
            return 0.0

    pending.sort(key=_mtime, reverse=True)
    if limit is not None:
        pending = pending[:limit]

    results = []
    for j in pending:
        jid = j.get("id", "")
        system_text = j.get("system", "")
        user_text = j.get("user", "")
        kind = guess_job_kind(system_text)
        person = extract_person(user_text)
        url = extract_url(user_text)
        content = extract_content(user_text)
        results.append(
            {
                "id": jid,
                "kind": kind,
                "person": person,
                "url": url,
                "content": content,
                "content_preview": content[:200]
                + ("..." if len(content) > 200 else ""),
                "full_user": user_text,
                "full_system": system_text,
            }
        )
    return results


def do_answer(
    job_id: str,
    json_input: str,
    jobs_dir: Path,
) -> Path:
    """Validate and write an answer for a job."""
    job_path = jobs_dir / f"{job_id}.job.json"
    if not job_path.exists():
        raise FileNotFoundError(f"Job file {job_path} does not exist")

    job_dict = json.loads(job_path.read_text(encoding="utf-8"))

    # Resolve input: either path to JSON file or raw JSON string
    p = Path(json_input)
    if p.exists() and p.is_file():
        answer_str = p.read_text(encoding="utf-8").strip()
    else:
        answer_str = json_input.strip()

    validate_answer(job_dict, answer_str)
    # Re-serialize to canonical JSON string
    canonical = json.dumps(json.loads(answer_str), ensure_ascii=False)
    return answer_job(job_id, canonical, jobs_dir=jobs_dir)


def do_prune(older_than_days: int, jobs_dir: Path) -> int:
    """Delete unanswered job files older than specified days.

    Never deletes a job file if a corresponding .response.json exists.
    Returns count of pruned jobs.
    """
    cutoff = time.time() - (older_than_days * 86400)
    pruned_count = 0
    for job_path in sorted(jobs_dir.glob("*.job.json")):
        resp_path = job_path.with_name(
            job_path.name.replace(".job.json", ".response.json")
        )
        if resp_path.exists():
            continue
        try:
            mtime = job_path.stat().st_mtime
            if mtime < cutoff:
                job_path.unlink()
                pruned_count += 1
        except Exception:
            continue
    return pruned_count


def resolve_repo_root(custom_repo: Path | None = None) -> Path:
    if custom_repo is not None:
        return Path(custom_repo).resolve()
    root = ROOT_DIR
    if (root / "agent_jobs").exists() and any((root / "agent_jobs").glob("*.job.json")):
        return root
    try:
        import subprocess

        common = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if common.returncode == 0 and common.stdout.strip():
            gitdir = Path(common.stdout.strip())
            if not gitdir.is_absolute():
                gitdir = root / gitdir
            parent = gitdir.resolve().parent
            if (parent / "agent_jobs").exists():
                return parent
    except Exception:
        pass
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Worker CLI for agent_jobs queue")
    parser.add_argument(
        "--repo",
        type=Path,
        default=ROOT_DIR,
        help="Path to repository root (defaults to parent of scripts/)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_p = subparsers.add_parser("list", help="List pending jobs")
    list_p.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to repository root (overrides top-level --repo)",
    )
    list_p.add_argument(
        "--limit", type=int, default=None, help="Max jobs to display"
    )

    # answer
    ans_p = subparsers.add_parser("answer", help="Validate and answer a job")
    ans_p.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to repository root (overrides top-level --repo)",
    )
    ans_p.add_argument("--job", required=True, help="Job ID")
    ans_p.add_argument(
        "--json",
        required=True,
        help="Inline JSON string or path to JSON file",
    )

    # prune
    prune_p = subparsers.add_parser("prune", help="Prune stale unanswered jobs")
    prune_p.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to repository root (overrides top-level --repo)",
    )
    prune_p.add_argument(
        "--older-than-days",
        type=int,
        default=7,
        help="Delete unanswered jobs older than N days (default 7)",
    )

    args = parser.parse_args(argv)
    repo_path = args.repo or ROOT_DIR
    jobs_dir = repo_path / "agent_jobs"

    if args.command == "list":
        items = do_list(jobs_dir, limit=args.limit)
        print(f"Pending jobs: {len(items)}")
        for it in items:
            print(f"- [{it['kind']}] {it['id']}")
            if it["url"]:
                print(f"  URL: {it['url']}")
            print(f"  Content: {it['content_preview']}\n")
        return 0

    elif args.command == "answer":
        try:
            resp_path = do_answer(args.job, args.json, jobs_dir)
            print(f"Successfully answered job {args.job} -> {resp_path.name}")
            return 0
        except Exception as exc:
            print(f"Error answering job {args.job}: {exc}", file=sys.stderr)
            return 1

    elif args.command == "prune":
        count = do_prune(args.older_than_days, jobs_dir)
        print(
            f"Pruned {count} unanswered job(s) older than {args.older_than_days} day(s)."
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
