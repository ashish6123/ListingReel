from supabase import Client


class StorageError(Exception):
    pass


def upload_file(
    db: Client,
    bucket: str,
    path: str,
    data: bytes,
    content_type: str,
) -> str:
    """Uploads bytes to a Supabase Storage bucket and returns the storage path.

    Use only on the backend with a service-role client - this bypasses Storage RLS.
    """
    try:
        db.storage.from_(bucket).upload(
            path,
            data,
            {"content-type": content_type, "upsert": "true"},
        )
    except Exception as exc:  # noqa: BLE001 - supabase-py raises plain Exception
        raise StorageError(f"Failed to upload to {bucket}/{path}: {exc}") from exc

    return path


def create_signed_url(db: Client, bucket: str, path: str, expires_in: int = 3600) -> str:
    try:
        result = db.storage.from_(bucket).create_signed_url(path, expires_in)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Failed to sign URL for {bucket}/{path}: {exc}") from exc

    signed_url = result.get("signedURL") or result.get("signed_url")
    if not signed_url:
        raise StorageError(f"Unexpected signed URL response: {result}")

    return signed_url


def download_file(db: Client, bucket: str, path: str) -> bytes:
    try:
        return db.storage.from_(bucket).download(path)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"Failed to download {bucket}/{path}: {exc}") from exc
