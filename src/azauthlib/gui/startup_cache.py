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

"""Disposable warm-start cache: bundled, prepared text only, never user/connection data."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from ..appdata import ensure_private_directory, get_cache_dir
from .legal_terms import POLICY_FILES

SCHEMA = 1
MAX_BYTES = 5 * 1024 * 1024


def _identity(resources):
    paths = [
        resources.path("assets", "docs", "legal", name)
        for name in (*POLICY_FILES.values(), "INDEPENDENCE_AND_NOTICES.md")
    ]
    paths.extend((Path(__file__), Path(__file__).with_name("legal_terms.py")))
    stamps = [(str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size) for path in paths]
    return hashlib.sha256(repr((SCHEMA, sys.version, stamps)).encode()).hexdigest()


def load_shared_content(resources, *, directory=None):
    try:
        target = (directory or get_cache_dir()) / "startup-content.json"
        if target.is_symlink() or target.stat().st_size > MAX_BYTES:
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        if payload.get("identity") != _identity(resources):
            return None
        documents, about = payload["documents"], payload["about"]
        if (
            not isinstance(documents, dict)
            or set(documents) != set(POLICY_FILES)
            or any(not isinstance(value, str) or not value for value in documents.values())
            or not isinstance(about, str)
            or not about
        ):
            return None
        return {"legalDocuments": documents, "aboutMarkdown": about}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None  # A missing/stale/corrupt cache always takes the normal path.


def save_shared_content(resources, documents, about, *, directory=None):
    temporary = None
    try:
        folder = ensure_private_directory(directory or get_cache_dir())
        target = folder / "startup-content.json"
        # Explicit allowlist: never serialize the full startup/controller state.
        data = json.dumps(
            {"identity": _identity(resources), "documents": documents, "about": about},
            ensure_ascii=True,
        ).encode("utf-8")
        if len(data) > MAX_BYTES or target.is_symlink():
            return
        descriptor, name = tempfile.mkstemp(prefix=".startup-", dir=folder)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except (OSError, TypeError, ValueError):
        pass  # Cache writes are optional and must never block a normal launch.
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def _image_path(source, key):
    renderer = Path(__file__).with_name("svg_images.py").stat()
    identity = repr((SCHEMA, str(source.resolve()), key, renderer.st_mtime_ns, renderer.st_size))
    name = hashlib.sha256(identity.encode()).hexdigest() + ".png"
    return get_cache_dir() / "startup-service-images" / name


def load_service_image(source, key, width, height):
    from PySide6.QtGui import QImage, QImageReader

    try:
        path = _image_path(source, key)
        if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
            return None
        reader = QImageReader(str(path), b"PNG")
        size = reader.size()
        # Validate the header before decoding an optional local raster cache.
        if size.width() != width or size.height() != height:
            return None
        image = reader.read()
        return None if image.isNull() else image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    except (OSError, RuntimeError):
        return None


def save_service_image(source, key, image):
    from PySide6.QtCore import QIODevice, QSaveFile

    try:
        path = _image_path(source, key)
        ensure_private_directory(path.parent)
        if path.is_symlink():
            return
        # Evict only hash-named thumbnails from this dedicated cache directory.
        # New app/asset revisions must not permanently fill the warm cache.
        if not path.exists():
            entries = [
                entry
                for entry in path.parent.glob("*.png")
                if len(entry.stem) == 64
                and all(char in "0123456789abcdef" for char in entry.stem)
                and not entry.is_symlink()
                and entry.is_file()
            ]
            entries.sort(key=lambda entry: entry.stat().st_mtime_ns)
            for expired in entries[: max(0, len(entries) - 63)]:
                if expired.resolve().parent != path.parent.resolve():
                    return
                expired.unlink()
        output = QSaveFile(str(path))
        if output.open(QIODevice.WriteOnly):
            if image.save(output, "PNG"):
                output.commit()
            else:
                output.cancelWriting()
    except (OSError, RuntimeError):
        pass


def prepare_warm_cache(resources, snapshots=(), cancelled=lambda: False):
    """Background preparation of shared text and logos, never service/profile state."""
    from .legal_terms import load_legal_documents
    from .svg_images import PROVIDER_LOGO_PATHS, ProviderLogoImageProvider

    if cancelled():
        return False
    if load_shared_content(resources) is None:
        legal = load_legal_documents(resources)
        about = resources.path("assets", "docs", "legal", "INDEPENDENCE_AND_NOTICES.md").read_text(
            encoding="utf-8"
        )
        if cancelled():
            return False
        save_shared_content(resources, legal["documents"], about)
    if load_shared_content(resources) is None:
        return False
    # Always prepare the baseline used by Main Menu; keep actual DPI-specific
    # sizes already rendered in this session as well. Snapshots own their QImages.
    prepared = {key: (path, image) for path, key, image in snapshots}
    requests = {(name, 384, 384) for name in PROVIDER_LOGO_PATHS}
    requests.update(key[:3] for key in prepared)
    for name, width, height in sorted(requests):
        if cancelled():
            return False
        path = resources.path("assets", *PROVIDER_LOGO_PATHS[name], name)
        stamp = path.stat()
        key = (name, width, height, stamp.st_mtime_ns, stamp.st_size)
        if load_service_image(path, key, width, height) is not None:
            continue
        snapshot = prepared.get(key)
        image = (
            snapshot[1]
            if snapshot is not None
            else ProviderLogoImageProvider._render(path, width, height)
        )
        if cancelled():
            return False
        save_service_image(path, key, image)
        if load_service_image(path, key, width, height) is None:
            return False
    return not cancelled()
