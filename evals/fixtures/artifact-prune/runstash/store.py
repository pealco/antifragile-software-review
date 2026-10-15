"""The bucket side. Each run is one object: <prefix>/<run>.tar.gz."""

from __future__ import annotations

import boto3
from boto3.s3.transfer import TransferConfig

from runstash.config import Config

SUFFIX = ".tar.gz"
_TRANSFER = TransferConfig(
    multipart_threshold=64 * 1024 * 1024,
    multipart_chunksize=64 * 1024 * 1024,
    max_concurrency=8,
)


class UploadMismatch(Exception):
    pass


def client(cfg: Config):
    return boto3.client("s3", region_name=cfg.region)


def key_for(cfg: Config, run: str) -> str:
    return f"{cfg.prefix}/{run}{SUFFIX}"


def upload(cfg: Config, run: str, archive, callback=None) -> None:
    client(cfg).upload_file(
        str(archive),
        cfg.bucket,
        key_for(cfg, run),
        ExtraArgs={"ChecksumAlgorithm": "SHA256"},
        Config=_TRANSFER,
        Callback=callback,
    )


def verify(cfg: Config, run: str, expected_size: int) -> None:
    """The SDK checks each part's SHA-256; this catches a wrong key or a truncated source."""
    head = client(cfg).head_object(Bucket=cfg.bucket, Key=key_for(cfg, run))
    if head["ContentLength"] != expected_size:
        raise UploadMismatch(
            f"{key_for(cfg, run)}: uploaded {head['ContentLength']} bytes, expected {expected_size}"
        )


def remote_runs(cfg: Config) -> dict[str, dict]:
    """Run name -> listing entry (Key, Size, LastModified) for every archive under the prefix."""
    runs: dict[str, dict] = {}
    pages = client(cfg).get_paginator("list_objects_v2").paginate(
        Bucket=cfg.bucket, Prefix=f"{cfg.prefix}/"
    )
    for page in pages:
        for obj in page.get("Contents", []):
            name = obj["Key"][len(cfg.prefix) + 1 :]
            if name.endswith(SUFFIX) and "/" not in name:
                runs[name[: -len(SUFFIX)]] = obj
    return runs
