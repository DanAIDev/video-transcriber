"""Provider-agnostic orchestration layer.

This module is *minimal*, giving you a working path from local media → Azure
Batch job submission → JSON transcript download. It is not yet feature-complete
(compared to the old monolithic script), but enough to demonstrate the new
architecture and let you run real batch transcriptions safely.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from moviepy.editor import VideoFileClip  # type: ignore

from providers.azure_batch import AzureBatchProvider  # default provider
from providers.base import AbstractTranscriptionProvider

logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """High-level workflow independent of any single STT backend."""

    def __init__(
        self,
        provider: AbstractTranscriptionProvider | None = None,
        job_log: Path | None = None,
    ) -> None:
        self.provider: AbstractTranscriptionProvider = provider or AzureBatchProvider()
        self.job_log_path = job_log or Path("jobs.json")
        self._jobs: Dict[str, Any] = self._load_jobs()

    # ------------------------------------------------------------------
    # Public entrypoints ------------------------------------------------

    def submit_single(self, media: Path, language: str = "en-US") -> str:
        """Submit one file and persist the returned job ID."""
        media = media.expanduser().resolve()
        job_id = self.provider.submit_job(media, language=language)
        self._jobs[job_id] = {
            "file": str(media),
            "submitted": time.time(),
            "language": language,
            "state": "submitted",
        }
        self._save_jobs()
        logger.info("Submitted %s → job %s", media.name, job_id)
        return job_id

    def submit_batch(self, directory: Path, language: str = "en-US") -> List[str]:
        """Submit every supported media file in *directory* recursively."""
        directory = directory.expanduser().resolve()
        jobs: List[str] = []
        for path in directory.rglob("*"):
            if path.suffix.lower() in {".mp4", ".wav", ".mp3", ".mkv", ".flac"}:
                try:
                    jobs.append(self.submit_single(path, language))
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Failed to submit %s: %s", path.name, exc)
        return jobs

    def poll(self, interval_sec: int = 30) -> None:
        """Poll all unfinished jobs until done."""
        unfinished = {jid: meta for jid, meta in self._jobs.items() if meta.get("state") not in {"succeeded", "failed"}}
        if not unfinished:
            logger.info("No unfinished jobs.")
            return
        while unfinished:
            for job_id in list(unfinished):
                status = self.provider.job_status(job_id)
                state = status.get("state", "unknown")
                self._jobs[job_id]["state"] = state
                logger.info("Job %s → %s", job_id, state)
                if state in {"Succeeded", "Failed", "succeeded", "failed"}:
                    if state.lower().startswith("succ"):
                        self._download_result(job_id)
                    unfinished.pop(job_id)
                    self._save_jobs()
            if unfinished:
                time.sleep(interval_sec)

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------

    def _download_result(self, job_id: str) -> None:
        dest = Path(f"{job_id}_transcript.json")
        try:
            path = self.provider.fetch_result(job_id, dest)
            self._jobs[job_id]["result"] = str(path)
            logger.info("Downloaded result for job %s → %s", job_id, path)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to fetch result for %s: %s", job_id, exc)

    # ------------------------------------------------------------------

    def _load_jobs(self) -> Dict[str, Any]:
        if self.job_log_path.exists():
            return json.loads(self.job_log_path.read_text("utf-8"))
        return {}

    def _save_jobs(self) -> None:
        self.job_log_path.write_text(json.dumps(self._jobs, indent=2), "utf-8")
