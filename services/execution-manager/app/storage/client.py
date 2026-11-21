"""S3-compatible object storage client.

Stores execution artefacts (test reports, patches, diffs) in S3-compatible
object storage (README §12.2, FR-5.3). Abstracted behind an interface so the
artefact service is testable without object storage.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class StoredObject:
    """A stored object location."""

    bucket: str
    key: str
    size_bytes: int


class ObjectStore(abc.ABC):
    """Minimal object-storage surface used by the artefact service."""

    @abc.abstractmethod
    def put(self, bucket: str, key: str, data: bytes, *, content_type: str | None = None) -> StoredObject:
        """Upload bytes and return the stored location."""

    @abc.abstractmethod
    def get(self, bucket: str, key: str) -> bytes:
        """Fetch stored bytes."""

    @abc.abstractmethod
    def delete(self, bucket: str, key: str) -> None:
        """Delete a stored object."""


class S3ObjectStore(ObjectStore):
    """Production object store backed by boto3 (lazily resolved)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: object | None = None

    def _resolve(self) -> object:
        if self._client is None:
            import boto3  # type: ignore[import-untyped]

            self._client = boto3.client(
                "s3",
                endpoint_url=self._settings.artifact_endpoint_url or None,
                aws_access_key_id=self._settings.artifact_access_key or None,
                aws_secret_access_key=self._settings.artifact_secret_key or None,
            )
        return self._client

    def put(self, bucket: str, key: str, data: bytes, *, content_type: str | None = None) -> StoredObject:
        client = self._resolve()
        kwargs: dict[str, object] = {"Bucket": bucket, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        client.put_object(**kwargs)  # type: ignore[operator]
        return StoredObject(bucket=bucket, key=key, size_bytes=len(data))

    def get(self, bucket: str, key: str) -> bytes:
        client = self._resolve()
        response = client.get_object(Bucket=bucket, Key=key)  # type: ignore[operator]
        body = response["Body"].read()  # type: ignore[index]
        return bytes(body)

    def delete(self, bucket: str, key: str) -> None:
        client = self._resolve()
        client.delete_object(Bucket=bucket, Key=key)  # type: ignore[operator]


class MemoryObjectStore(ObjectStore):
    """In-memory object store for tests and local development."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, bucket: str, key: str, data: bytes, *, content_type: str | None = None) -> StoredObject:
        self._objects[f"{bucket}/{key}"] = data
        return StoredObject(bucket=bucket, key=key, size_bytes=len(data))

    def get(self, bucket: str, key: str) -> bytes:
        return self._objects[f"{bucket}/{key}"]

    def delete(self, bucket: str, key: str) -> None:
        self._objects.pop(f"{bucket}/{key}", None)