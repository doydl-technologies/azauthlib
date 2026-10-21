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

"""GUI process-lock helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import portalocker

logger = logging.getLogger(__name__)


def enforce_single_instance(lockfile):
    path = Path(lockfile)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        return portalocker.Lock(str(path), mode="a", timeout=0).acquire()
    except portalocker.exceptions.AlreadyLocked:
        return None


def on_exit(lock, lockfile=None):
    del lockfile
    if lock is None:
        return
    try:
        portalocker.unlock(lock)
    finally:
        lock.close()
