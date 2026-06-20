"""Security regression tests for storage-path ownership validation.

Storage uploads are scoped per-user as `{user_id}/{listing_id}/{file}.jpg`
(enforced client-side by image-uploader.tsx and by Storage RLS on upload).
But `POST /api/listings` previously trusted whatever path strings the client
sent in `image_urls` with no ownership check, and the backend signs/reads
those paths using the service-role client - which bypasses Storage RLS
entirely. This let any authenticated user submit another user's storage
path and have it baked into their own listing (and later their own video).
"""

import pytest
from fastapi import HTTPException

from app.routers.listings import _assert_owns_image_paths


def test_rejects_another_users_storage_path():
    attacker_id = "11111111-1111-1111-1111-111111111111"
    victim_id = "22222222-2222-2222-2222-222222222222"
    victim_path = f"{victim_id}/some-listing-id/photo.jpg"

    with pytest.raises(HTTPException) as exc_info:
        _assert_owns_image_paths(attacker_id, [victim_path])
    assert exc_info.value.status_code == 403


def test_rejects_mixed_own_and_foreign_paths():
    """Even one foreign path mixed in with otherwise-legitimate paths must
    be rejected, not silently dropped or partially accepted."""
    user_id = "11111111-1111-1111-1111-111111111111"
    other_id = "22222222-2222-2222-2222-222222222222"
    paths = [
        f"{user_id}/listing-a/photo1.jpg",
        f"{other_id}/listing-b/photo2.jpg",
    ]

    with pytest.raises(HTTPException) as exc_info:
        _assert_owns_image_paths(user_id, paths)
    assert exc_info.value.status_code == 403


def test_accepts_own_paths():
    user_id = "11111111-1111-1111-1111-111111111111"
    paths = [
        f"{user_id}/listing-a/photo1.jpg",
        f"{user_id}/listing-a/photo2.jpg",
    ]
    # Should not raise
    _assert_owns_image_paths(user_id, paths)


def test_accepts_empty_list():
    _assert_owns_image_paths("11111111-1111-1111-1111-111111111111", [])


def test_rejects_path_without_any_prefix():
    """A bare filename with no user-id prefix at all must also be rejected,
    not just paths that look like a *different* user's folder."""
    user_id = "11111111-1111-1111-1111-111111111111"
    with pytest.raises(HTTPException) as exc_info:
        _assert_owns_image_paths(user_id, ["just-a-filename.jpg"])
    assert exc_info.value.status_code == 403


def test_rejects_prefix_lookalike_attack():
    """A user-id that is a *prefix* of another user-id (or vice versa)
    must not be confused - the check must require a path separator after
    the user_id, not just startswith on the raw string."""
    user_id = "11111111-1111-1111-1111-111111111111"
    lookalike_user_id = "11111111-1111-1111-1111-1111111111112"  # extra digit
    path = f"{lookalike_user_id}/listing/photo.jpg"

    with pytest.raises(HTTPException) as exc_info:
        _assert_owns_image_paths(user_id, [path])
    assert exc_info.value.status_code == 403
