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

"""Tests for delegated and application scope normalization."""

import pytest

from azauthlib.permissions import GRAPH_DEFAULT_SCOPE, application_scope_fmt, scope_fmt


def test_delegated_scope_normalization():
    assert scope_fmt(scopes="Mail.Read User.Read Mail.Read") == ["Mail.Read", "User.Read"]


def test_delegated_default():
    assert scope_fmt() == ["User.Read"]


def test_application_scope_default():
    assert application_scope_fmt() == [GRAPH_DEFAULT_SCOPE]


def test_application_scope_rejects_individual_permission():
    with pytest.raises(ValueError, match="/.default"):
        application_scope_fmt("Files.ReadWrite.All")


def test_default_cannot_be_mixed_with_dynamic_scopes():
    with pytest.raises(ValueError, match="cannot be combined"):
        scope_fmt(scopes=[GRAPH_DEFAULT_SCOPE, "User.Read"])
