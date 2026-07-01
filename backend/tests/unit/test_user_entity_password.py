"""Unit tests for User password-change tracking (session-invalidation support)."""

from __future__ import annotations

from src.domain.users.entities import User


def test_create_sets_password_changed_at() -> None:
    user = User.create(email="a@b.com", hashed_password="hash")
    assert user.password_changed_at == user.created_at


def test_update_password_bumps_password_changed_at() -> None:
    user = User.create(email="a@b.com", hashed_password="old")
    before = user.password_changed_at

    user.update_password("new")

    assert user.hashed_password == "new"
    assert user.password_changed_at >= before
    # password_changed_at moves in lockstep with updated_at on a password change.
    assert user.password_changed_at == user.updated_at
