"""Temporary handling of uploaded originals (letter and document photos).

What the framework does (audited for starlette 1.8 / FastAPI 0.143): each
uploaded file is spooled into a tempfile.SpooledTemporaryFile that stays in
memory up to 1 MB and above that rolls over to an anonymous temporary file
in the OS temp directory (unlinked at creation on macOS/Linux, but its data
sits on disk until closed, and closing frees the space without overwriting
it). FastAPI only closes it after the response is sent. So here we:

- read the upload into our own bytearray (capped at MAX_UPLOAD_BYTES),
- close the upload ourselves as soon as we have it, in a `finally`, so
  success, failure and cancellation all release it,
- overwrite our bytearray with zeros when processing ends.

Limits: copies made elsewhere (the HTTP parser's buffers, base64 encoding
for OCI, the OCI SDK's HTTP client) can't be wiped from Python and are
freed by the garbage collector at an unspecified time; zeroing is
best-effort, not guaranteed erasure. The browser shrinks photos below 1 MB
before upload so they normally never spill to disk -- not guaranteed if
that step fails. See docs/PRIVACY.md.
"""

from __future__ import annotations

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_CHUNK = 256 * 1024


class UploadTooLarge(Exception):
    pass


async def read_and_close(upload: UploadFile) -> bytearray:
    """Read the upload into a bytearray we control and close it -- always,
    including when reading fails or the request is cancelled."""
    buffer = bytearray()
    try:
        while chunk := await upload.read(_CHUNK):
            buffer += chunk
            if len(buffer) > MAX_UPLOAD_BYTES:
                wipe(buffer)
                raise UploadTooLarge()
        return buffer
    except BaseException:
        wipe(buffer)
        raise
    finally:
        await upload.close()


def wipe(buffer: bytearray | None) -> None:
    """Best-effort: overwrite our copy of an original with zeros."""
    if buffer:
        buffer[:] = bytes(len(buffer))
