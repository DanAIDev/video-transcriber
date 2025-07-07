"""Azure Batch Transcription provider implementation.

Only the *wire-up* to the REST API is provided here. Uploading media to Blob
Storage and authenticating with Azure AD / subscription key must be configured
via environment variables or a .env file:

* AZURE_SPEECH_KEY           – Speech resource key (if using key auth)
* AZURE_SPEECH_REGION        – Resource region, e.g. ``eastus``
* AZURE_SPEECH_ENDPOINT      – Optional custom endpoint.
* AZURE_SPEECH_SUBSCRIPTION  – (alternative name some users prefer)

In addition, you need:

* INPUT_CONTAINER_SAS_URL    – SAS URI of the container where *source* audio
                                 already resides (or will be uploaded by an
                                 external step).
* OUTPUT_CONTAINER_SAS_URL   – SAS URI of the container where results will be
                                 written by the Speech service.

Uploading is *not* handled here; see ``utils/blob.py`` (future work) or upload
manually before calling ``submit_job``.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from azure.storage.blob import ContainerClient, ContentSettings
from dotenv import load_dotenv

from .base import AbstractTranscriptionProvider

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------

load_dotenv()

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY") or os.getenv("AZURE_SPEECH_SUBSCRIPTION")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
SPEECH_ENDPOINT = os.getenv("AZURE_SPEECH_ENDPOINT", f"https://{SPEECH_REGION}.api.cognitive.microsoft.com")

INPUT_CONTAINER = os.getenv("INPUT_CONTAINER_SAS_URL")
OUTPUT_CONTAINER = os.getenv("OUTPUT_CONTAINER_SAS_URL")

if not all([SPEECH_KEY, INPUT_CONTAINER, OUTPUT_CONTAINER]):
    # The provider can still be imported, but submit_job will raise.
    pass


class AzureBatchProvider(AbstractTranscriptionProvider):
    """Concrete provider using Azure Speech Batch Transcription REST API."""

    def __init__(self):
        if not all([SPEECH_KEY, INPUT_CONTAINER, OUTPUT_CONTAINER]):
            raise RuntimeError("AzureBatchProvider environment variables missing. See docs in providers.azure_batch module docstring.")

        self._headers = {
            "Ocp-Apim-Subscription-Key": SPEECH_KEY,
            "Content-Type": "application/json"
        }
        self._base_url = f"{SPEECH_ENDPOINT}/speechtotext/v3.1"
        # Container client for uploading local media
        self._input_container = ContainerClient.from_container_url(INPUT_CONTAINER)

    # ------------------------------------------------------------------
    # Abstract methods --------------------------------------------------

    def submit_job(self, media_path: Path, *, language: str = "en-US") -> str:
        """Submit a local file or an already uploaded blob to Azure Batch.

        If *media_path* points to an existing **local** file, it is uploaded to
        the *input* container with the blob name ``media_path.name`` before the
        REST request is sent.

        Parameters
        ----------
        media_path:
            Local ``Path`` *or* dummy ``Path`` whose ``name`` matches an audio
            blob already present in the container. No attempt is made to infer
            sub-folders; the blob will always live at the container root.
        language:
            BCP-47 locale (default "en-US").

        Returns
        -------
        str
            The Azure transcription job ID.
        """
        # Upload if needed
        if media_path.exists():
            blob_name = media_path.name
            with open(media_path, "rb") as fh:
                self._input_container.upload_blob(
                    name=blob_name,
                    data=fh,
                    overwrite=True,
                    content_settings=ContentSettings(content_type="audio/wav"),
                )
        else:
            blob_name = media_path.name  # assume already uploaded / remote

        blob_uri = f"{INPUT_CONTAINER.rstrip('/')}/{blob_name}"
        payload = {
            "contentUrls": [blob_uri],
            "locale": language,
            "displayName": f"Transcription {media_path.name} {int(time.time())}",
            "properties": {
                "wordLevelTimestampsEnabled": True,
                "punctuationMode": "DictatedAndAutomaticPunctuation",
                "profanityFilterMode": "Masked",
                "destinationContainerUrl": OUTPUT_CONTAINER,
            },
        }
        url = f"{self._base_url}/transcriptions"
        response = requests.post(url, headers=self._headers, data=json.dumps(payload))
        response.raise_for_status()
        # The operation is async; Location header contains job URL.
        job_url: str = response.headers.get("Location")
        job_id = job_url.rsplit("/", 1)[-1]
        return job_id

    def job_status(self, job_id: str) -> Dict[str, Any]:
        url = f"{self._base_url}/transcriptions/{job_id}"
        r = requests.get(url, headers=self._headers)
        r.raise_for_status()
        data = r.json()
        return {
            "state": data.get("status"),
            "raw": data,
        }

    def fetch_result(self, job_id: str, destination: Path) -> Path:
        # Results are written by the service to OUTPUT_CONTAINER as
        # <jobId>.json (plus per-file transcripts). We simply download that.
        blob_url = f"{OUTPUT_CONTAINER.rstrip('/')}/{job_id}.json"
        r = requests.get(blob_url)
        r.raise_for_status()
        destination = destination.with_suffix(".json")
        destination.write_bytes(r.content)
        return destination
