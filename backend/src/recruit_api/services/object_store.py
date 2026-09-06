"""Object storage for résumé PDFs and (later) generated reports.

S3-compatible; MinIO locally. boto3 is sync, so the S3 impl offloads calls to a
thread. Tests use ``InMemoryObjectStore``.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from ..config import Settings


class ObjectNotFound(Exception):
    pass


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> int: ...


class InMemoryObjectStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self._objects[key] = data

    async def get(self, key: str) -> bytes:
        try:
            return self._objects[key]
        except KeyError as exc:
            raise ObjectNotFound(key) from exc

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        victims = [k for k in self._objects if k.startswith(prefix)]
        for k in victims:
            del self._objects[k]
        return len(victims)


class S3ObjectStore:
    def __init__(
        self, *, endpoint: str, bucket: str, access_key: str, secret_key: str, region: str
    ):
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        try:
            resp = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        except self._client.exceptions.NoSuchKey as exc:
            raise ObjectNotFound(key) from exc
        return await asyncio.to_thread(resp["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def delete_prefix(self, prefix: str) -> int:
        def _run() -> int:
            paginator = self._client.get_paginator("list_objects_v2")
            removed = 0
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if not keys:
                    continue
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": keys})
                removed += len(keys)
            return removed

        return await asyncio.to_thread(_run)


def build_object_store(settings: Settings) -> ObjectStore:
    return S3ObjectStore(
        endpoint=settings.s3_endpoint,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )
