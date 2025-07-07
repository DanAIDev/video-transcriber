"""Base classes and contracts for transcription providers.

A *provider* is an implementation that knows how to:
1. Accept an audio (or video) file URI and create an asynchronous transcription job.
2. Poll or query the state of an existing job.
3. Download the final transcription artefacts to a local destination.

The surrounding application (see ``core.pipeline``) is provider-agnostic;
all interactions must go through the ``AbstractTranscriptionProvider`` API below.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class AbstractTranscriptionProvider(ABC):
    """SPI for pluggable speech-to-text back-ends."""

    # ---- Job submission -------------------------------------------------
    @abstractmethod
    def submit_job(self, media_path: Path, *, language: str = "en-US") -> str:
        """Start an asynchronous transcription job.

        Parameters
        ----------
        media_path:
            Local file that *has already been uploaded* or is otherwise
            accessible to the provider implementation. The contract for whether
            the provider automatically uploads or expects a URI is left to the
            concrete class.
        language:
            BCP-47 language code (default ``en-US``).

        Returns
        -------
        str
            Provider-specific job identifier that can be used with
            ``job_status`` and ``fetch_result``.
        """

    # ---- Job status -----------------------------------------------------
    @abstractmethod
    def job_status(self, job_id: str) -> Dict[str, Any]:
        """Return the current status of a job.

        Implementations should at minimum return a dictionary containing a
        ``state`` key whose value is one of ``queued``, ``running``,
        ``succeeded`` or ``failed``. Additional provider-specific metadata is
        allowed.
        """

    # ---- Retrieve final artefacts --------------------------------------
    @abstractmethod
    def fetch_result(self, job_id: str, destination: Path) -> Path:
        """Download or generate the final transcript for ``job_id``.

        The concrete class is responsible for choosing the appropriate result
        format (JSON, plain text, etc.) and placing it at ``destination``.

        Returns
        -------
        Path
            The path of the file that was written.
        """

    # ---- Optional clean-up ---------------------------------------------
    def cancel_job(self, job_id: str) -> None:  # pragma: no cover – optional
        """Attempt to cancel an in-flight transcription job.

        Providers *may* implement this; the default does nothing.
        """
        return None
