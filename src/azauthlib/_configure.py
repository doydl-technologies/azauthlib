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

"""Side-effect-free application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .profiles import profile_config_path, profile_token_path


@dataclass(frozen=True)
class Settings:
    env_path: Path
    token_path: Path


def get_settings(profile=None) -> Settings:
    return Settings(
        env_path=profile_config_path(profile),
        token_path=profile_token_path(profile),
    )


class _SettingsProxy:
    @property
    def default_env_path(self) -> str:
        return str(get_settings().env_path)

    @property
    def default_token_path(self) -> str:
        return str(get_settings().token_path)


konfigurasie = _SettingsProxy()

__all__ = ["Settings", "get_settings", "konfigurasie"]
