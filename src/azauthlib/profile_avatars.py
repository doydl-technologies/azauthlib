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

"""The bundled SVG choices for a connection's optional display avatar."""

from functools import lru_cache
from importlib.resources import files

AVATAR_ASSET_PARTS = ("icons", "svg", "third-party", "profile-avatar")
EXCLUDED_PROFILE_AVATARS = frozenset(
    {
        "sql-server-registries.svg",
        "sql-server.svg",
        "sql-database.svg",
        "storage-accounts-classic.svg",
        "storage-accounts.svg",
        "subscriptions.svg",
    }
)


@lru_cache(maxsize=1)
def profile_avatar_names() -> tuple[str, ...]:
    """Discover packaged SVGs only; never accept an arbitrary file or URL."""
    directory = files("azauthlib").joinpath("assets", *AVATAR_ASSET_PARTS)
    try:
        return tuple(
            sorted(
                entry.name
                for entry in directory.iterdir()
                if entry.is_file()
                and entry.name.endswith(".svg")
                and entry.name.casefold() not in EXCLUDED_PROFILE_AVATARS
            )
        )
    except OSError:
        return ()


def normalized_profile_avatar(value: object) -> str:
    """Unavailable or excluded artwork falls back to the default plug."""
    return value if isinstance(value, str) and value in profile_avatar_names() else ""
