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

"""Scope normalization for Microsoft identity platform authentication flows."""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_DELEGATED_SCOPE = "User.Read"
GRAPH_DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


def _as_scope_list(scopes, *, default: str) -> list[str]:
    if scopes is None:
        values = [default]
    elif isinstance(scopes, str):
        values = scopes.split()
    elif isinstance(scopes, Iterable):
        values = list(scopes)
    else:
        raise TypeError("scopes must be a string, iterable of strings, or None")
    if not values or any(not isinstance(scope, str) or not scope.strip() for scope in values):
        raise ValueError("At least one non-empty scope is required")
    normalized = [scope.strip() for scope in values]
    if any(any(ord(char) < 0x20 for char in scope) for scope in normalized):
        raise ValueError("Scopes must not contain control characters")
    return list(dict.fromkeys(normalized))


def scope_fmt(permissions=None, scopes=None) -> list[str]:
    """Normalize delegated scopes.

    ``permissions`` remains accepted for compatibility but is no longer used.
    Microsoft Graph adds permissions over time, so a bundled allow-list cannot
    safely establish whether a delegated scope is valid.
    """
    del permissions
    result = _as_scope_list(scopes, default=DEFAULT_DELEGATED_SCOPE)
    if any(scope.endswith("/.default") for scope in result) and len(result) > 1:
        raise ValueError("A .default scope cannot be combined with dynamic delegated scopes")
    return result


def application_scope_fmt(scopes=None) -> list[str]:
    """Normalize scopes for client-credentials authentication.

    Microsoft requires ``{resource}/.default`` for this flow.
    """
    result = _as_scope_list(scopes, default=GRAPH_DEFAULT_SCOPE)
    if any(not scope.endswith("/.default") for scope in result):
        raise ValueError("Client credentials scopes must use the {resource}/.default form")
    return result


__all__ = [
    "DEFAULT_DELEGATED_SCOPE",
    "GRAPH_DEFAULT_SCOPE",
    "application_scope_fmt",
    "scope_fmt",
]
