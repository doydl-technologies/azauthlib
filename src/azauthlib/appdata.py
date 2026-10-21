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

"""Application data locations and safe filesystem helpers.

Importing this module never creates, modifies, or removes files. Callers must
explicitly request directory creation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from platformdirs import user_cache_path, user_config_path

APP_NAME = "azauthlib"
# False tells platformdirs not to insert an additional vendor directory on
# Windows. The resulting root is %LOCALAPPDATA%\azauthlib.
APP_AUTHOR: Literal[False] = False


def get_config_dir(*, create: bool = False) -> Path:
    path = user_config_path(APP_NAME, APP_AUTHOR, roaming=False)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def get_cache_dir(*, create: bool = False) -> Path:
    path = user_cache_path(APP_NAME, APP_AUTHOR)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def ensure_private_directory(path: str | os.PathLike[str]) -> Path:
    directory = Path(path).expanduser().resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    if os.name != "nt":
        directory.chmod(0o700)
    return directory


def ensure_within(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> Path:
    candidate = Path(path).expanduser().resolve()
    boundary = Path(root).expanduser().resolve()
    try:
        candidate.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(f"Path {candidate} is outside the allowed directory {boundary}") from exc
    return candidate


def find_default_user_data_dir() -> str:
    """Compatibility wrapper returning the deterministic configuration directory."""
    return str(get_config_dir(create=False))


class UserDataDirectory:
    """Compatibility wrapper around a deterministic application directory."""

    def __init__(self, dirname: str, auto_remove: bool = False):
        if auto_remove:
            raise ValueError("Automatic recursive deletion is no longer supported")
        if not dirname or Path(dirname).name != dirname:
            raise ValueError("dirname must be one safe path component")
        self.base_user_data_dir = get_config_dir(create=False)
        self.dirname = dirname

    def Dir(self) -> str:
        return str(ensure_private_directory(self.base_user_data_dir / self.dirname))

    def Exists(self, otherdir=None, exists_only=False):
        path = Path(otherdir) if otherdir else self.base_user_data_dir / self.dirname
        path = ensure_within(path, self.base_user_data_dir)
        exists = path.is_dir()
        return exists if exists_only else (str(path) if exists else None)

    def Omit(self, path: str) -> None:
        target = ensure_within(path, self.base_user_data_dir)
        target.rmdir()

    def DirFile(
        self,
        filename: str,
        extension: str,
        existing: bool = False,
        existing_path=None,
        overwrite: bool = False,
    ) -> str:
        del existing
        directory = ensure_private_directory(existing_path or self.Dir())
        if Path(filename).name != filename:
            raise ValueError("filename must not contain path separators")
        suffix = extension if extension.startswith(".") else f".{extension}"
        path = ensure_within(directory / f"{filename}{suffix}", self.base_user_data_dir)
        if overwrite or not path.exists():
            flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if overwrite else os.O_EXCL)
            try:
                fd = os.open(path, flags, 0o600)
            except FileExistsError:
                pass
            else:
                os.close(fd)
        return str(path)

    def Clean(self, alldirs: bool = False) -> None:
        del alldirs
        raise RuntimeError("Recursive application-data cleanup has been removed for safety")
