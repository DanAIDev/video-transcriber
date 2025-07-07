# Providers package

from .base import AbstractTranscriptionProvider

try:
    from .azure_batch import AzureBatchProvider  # noqa: F401
except ImportError:
    # Azure-specific dependencies may not be available yet; ignore import errors at package level.
    pass
