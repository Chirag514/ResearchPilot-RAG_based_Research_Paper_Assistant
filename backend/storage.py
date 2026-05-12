from backend.clients import get_supabase_admin

BUCKET = "pdfs"


def _storage():
    return get_supabase_admin().storage.from_(BUCKET)


def pdf_storage_path(user_id: str, session_id: str, filename: str) -> str:
    """Consistent path: {user_prefix}/{session_id}/{filename}"""
    return f"{str(user_id)[:8]}/{session_id}/{filename}"


def upload_pdf(user_id: str, session_id: str, filename: str, file_bytes: bytes) -> str:
    """Upload PDF to Supabase Storage. Returns storage path."""
    path = pdf_storage_path(user_id, session_id, filename)
    try:
        _storage().remove([path])           # remove old version if exists
    except Exception:
        pass
    _storage().upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": "application/pdf"}
    )
    return path


def get_pdf_url(path: str, expires_in: int = 21600) -> str:
    """Get a temporary signed URL (6 hour expiry) — works with private buckets.
    Each call generates a fresh URL so expired links are never shown to users.
    """
    res = _storage().create_signed_url(path, expires_in)
    return res["signedURL"]

def delete_pdf(path: str):
    """Delete a single PDF from storage."""
    try:
        _storage().remove([path])
    except Exception:
        pass


def delete_session_pdfs(user_id: str, session_id: str):
    """Delete all PDFs for an entire session folder."""
    prefix = f"{str(user_id)[:8]}/{session_id}"
    try:
        files = _storage().list(prefix)
        if files:
            paths = [f"{prefix}/{f['name']}" for f in files]
            _storage().remove(paths)
    except Exception:
        pass
