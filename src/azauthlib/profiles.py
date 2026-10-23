# -*- coding: utf-8 -*-

#
# DOYDL's Microsoft Identity Authentication Library — azauthlib
#
# Copyright 2024 DOYDL Technologies.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Named application profiles with isolated public configuration and token caches."""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .appdata import ensure_private_directory, ensure_within, get_cache_dir, get_config_dir
from .profile_avatars import normalized_profile_avatar

DEFAULT_PROFILE_ID = "default"
DEFAULT_PROFILE_NAME = "Default"
_REGISTRY_FILENAME = "profiles.json"
_REGISTRY_VERSION = 1
_MAX_PROFILE_NAME_LENGTH = 64


class ProfileStoreError(RuntimeError):
    """Raised when the profile registry cannot be read or written safely."""


@dataclass(frozen=True, slots=True)
class Profile:
    """A stable profile identifier and its user-facing name."""

    id: str
    name: str
    avatar: str = ""


def _default_registry() -> dict[str, Any]:
    return {
        "version": _REGISTRY_VERSION,
        "active": DEFAULT_PROFILE_ID,
        "profiles": [{"id": DEFAULT_PROFILE_ID, "name": DEFAULT_PROFILE_NAME}],
    }


def _registry_path() -> Path:
    return get_config_dir(create=False) / _REGISTRY_FILENAME


def _validated_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("profile name must be a string")
    normalized = name.strip()
    if not normalized:
        raise ValueError("Profile name is required.")
    if len(normalized) > _MAX_PROFILE_NAME_LENGTH:
        raise ValueError(f"Profile name must be {_MAX_PROFILE_NAME_LENGTH} characters or fewer.")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in normalized):
        raise ValueError("Profile name contains unsupported control characters.")
    return normalized


def _validate_registry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != _REGISTRY_VERSION:
        raise ProfileStoreError("The azauthlib profile registry has an unsupported format.")
    raw_profiles = value.get("profiles")
    if not isinstance(raw_profiles, list):
        raise ProfileStoreError("The azauthlib profile registry is malformed.")

    profiles: list[dict[str, str]] = []
    ids: set[str] = set()
    names: set[str] = set()
    for raw_profile in raw_profiles:
        if not isinstance(raw_profile, dict):
            raise ProfileStoreError("The azauthlib profile registry is malformed.")
        profile_id = raw_profile.get("id")
        profile_name = raw_profile.get("name")
        if not isinstance(profile_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", profile_id):
            raise ProfileStoreError("The azauthlib profile registry contains an invalid ID.")
        try:
            profile_name = _validated_name(profile_name)
        except (TypeError, ValueError) as exc:
            raise ProfileStoreError(
                "The azauthlib profile registry contains an invalid name."
            ) from exc
        folded_name = profile_name.casefold()
        if profile_id in ids or folded_name in names:
            raise ProfileStoreError("The azauthlib profile registry contains duplicate profiles.")
        ids.add(profile_id)
        names.add(folded_name)
        entry = {"id": profile_id, "name": profile_name}
        if avatar := normalized_profile_avatar(raw_profile.get("avatar")):
            entry["avatar"] = avatar
        profiles.append(entry)

    active = value.get("active")
    if not profiles:
        if "active" not in value or active is not None:
            raise ProfileStoreError("An empty profile registry must have no active profile.")
    elif not isinstance(active, str) or active not in ids:
        raise ProfileStoreError("The active azauthlib profile does not exist.")
    return {"version": _REGISTRY_VERSION, "active": active, "profiles": profiles}


def _read_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.is_file():
        return _default_registry()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileStoreError("Unable to read the azauthlib profile registry.") from exc
    return _validate_registry(value)


def _write_registry(registry: dict[str, Any]) -> None:
    registry = _validate_registry(registry)
    target = _registry_path()
    ensure_private_directory(target.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent, text=True
    )
    try:
        if os.name != "nt":
            os.chmod(temporary_name, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(registry, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except Exception:
        with suppress(FileNotFoundError):
            os.unlink(temporary_name)
        raise


def _profile_from_entry(entry: dict[str, str]) -> Profile:
    return Profile(id=entry["id"], name=entry["name"], avatar=entry.get("avatar", ""))


def list_profiles() -> tuple[Profile, ...]:
    """Return profiles in display order; a deliberately empty registry stays empty."""

    return tuple(_profile_from_entry(entry) for entry in _read_registry()["profiles"])


def resolve_profile(profile: str | Profile | None = None) -> Profile:
    """Resolve a profile by ID or case-insensitive display name."""

    registry = _read_registry()
    if profile is None:
        requested = registry["active"]
        if requested is None:
            raise ValueError("No connections are saved. Add a connection first.")
    elif isinstance(profile, Profile):
        requested = profile.id
    else:
        requested = profile
    if not isinstance(requested, str):
        raise TypeError("profile must be a profile name, ID, Profile instance, or None")
    folded = requested.casefold()
    for entry in registry["profiles"]:
        if entry["id"] == requested or entry["name"].casefold() == folded:
            return _profile_from_entry(entry)
    raise ValueError(f"Unknown azauthlib profile: {requested}")


def active_profile() -> Profile:
    """Return the currently selected default profile."""

    return resolve_profile()


def _validated_avatar(avatar: str) -> str:
    if not isinstance(avatar, str) or (avatar and normalized_profile_avatar(avatar) != avatar):
        raise ValueError("Choose an avatar from the available images.")
    return avatar


def create_profile(name: str, *, select: bool = True, avatar: str = "") -> Profile:
    """Create a profile; the first after an empty registry always becomes active."""

    normalized = _validated_name(name)
    avatar = _validated_avatar(avatar)
    registry = _read_registry()
    if any(entry["name"].casefold() == normalized.casefold() for entry in registry["profiles"]):
        raise ValueError(f'A profile named "{normalized}" already exists.')
    profile = Profile(id=uuid4().hex, name=normalized, avatar=avatar)
    entry = {"id": profile.id, "name": profile.name}
    if avatar:
        entry["avatar"] = avatar
    registry["profiles"].append(entry)
    if select or registry["active"] is None:
        registry["active"] = profile.id
    _write_registry(registry)
    return profile


def select_profile(profile: str | Profile) -> Profile:
    """Make an existing profile the active default."""

    selected = resolve_profile(profile)
    registry = _read_registry()
    if registry["active"] != selected.id:
        registry["active"] = selected.id
        _write_registry(registry)
    return selected


def rename_profile(profile: str | Profile, name: str, *, avatar: str | None = None) -> Profile:
    """Rename a connection without changing its configuration/cache identity."""

    selected = resolve_profile(profile)
    avatar = selected.avatar if avatar is None else _validated_avatar(avatar)
    normalized = _validated_name(name)
    registry = _read_registry()
    if any(
        entry["id"] != selected.id and entry["name"].casefold() == normalized.casefold()
        for entry in registry["profiles"]
    ):
        raise ValueError(f'A profile named "{normalized}" already exists.')
    if normalized != selected.name or avatar != selected.avatar:
        for entry in registry["profiles"]:
            if entry["id"] == selected.id:
                entry["name"] = normalized
                if avatar:
                    entry["avatar"] = avatar
                else:
                    entry.pop("avatar", None)
        _write_registry(registry)
    return Profile(selected.id, normalized, avatar)


def set_profile_avatar(profile: str | Profile, avatar: str) -> Profile:
    """Persist display artwork without touching credentials, caches or selection."""
    avatar = _validated_avatar(avatar)
    selected = resolve_profile(profile)
    if selected.avatar == avatar:
        return selected
    registry = _read_registry()
    for entry in registry["profiles"]:
        if entry["id"] == selected.id:
            if avatar:
                entry["avatar"] = avatar
            else:
                entry.pop("avatar", None)
            break
    _write_registry(registry)
    return Profile(selected.id, selected.name, avatar)


def remove_profile(profile: str | Profile) -> Profile:
    """Remove a registry entry and recoverably archive only its known files.

    Secrets are keyed by client ID, so other connections may share them. Never
    delete a keyring secret here. An empty registry has no active connection.
    """

    selected = resolve_profile(profile)
    registry = _read_registry()
    config_root = get_config_dir(create=False).resolve()
    cache_root = get_cache_dir(create=False).resolve()
    config = ensure_within(profile_config_path(selected), config_root)
    cache = ensure_within(profile_token_path(selected), cache_root)
    lock = ensure_within(Path(str(cache) + ".lockfile"), cache_root)
    archive_id = f"{selected.id}-{uuid4().hex}"
    moved: list[tuple[Path, Path]] = []
    try:
        for source, boundary in ((config, config_root), (cache, cache_root), (lock, cache_root)):
            if source.is_file():
                destination = ensure_within(
                    boundary / "removed-profiles" / archive_id / source.name, boundary
                )
                ensure_private_directory(destination.parent)
                os.replace(source, destination)
                moved.append((source, destination))
        registry["profiles"] = [
            entry for entry in registry["profiles"] if entry["id"] != selected.id
        ]
        if registry["active"] == selected.id:
            registry["active"] = registry["profiles"][0]["id"] if registry["profiles"] else None
        _write_registry(registry)
    except Exception:
        # A registry-write failure must not strand the still-registered files.
        for source, destination in reversed(moved):
            os.replace(destination, source)
        raise
    return selected


def profile_config_path(profile: str | Profile | None = None) -> Path:
    """Return the exact public configuration path for one profile."""

    selected = resolve_profile(profile)
    if selected.id == DEFAULT_PROFILE_ID:
        return get_config_dir(create=False) / ".env"
    return get_config_dir(create=False) / "profiles" / selected.id / ".env"


def profile_token_path(profile: str | Profile | None = None) -> Path:
    """Return the isolated encrypted MSAL cache path for one profile."""

    selected = resolve_profile(profile)
    if selected.id == DEFAULT_PROFILE_ID:
        return get_cache_dir(create=False) / "msal-cache.bin"
    return get_cache_dir(create=False) / "profiles" / selected.id / "msal-cache.bin"


__all__ = [
    "DEFAULT_PROFILE_ID",
    "DEFAULT_PROFILE_NAME",
    "Profile",
    "ProfileStoreError",
    "active_profile",
    "create_profile",
    "list_profiles",
    "profile_config_path",
    "profile_token_path",
    "remove_profile",
    "rename_profile",
    "resolve_profile",
    "select_profile",
]
