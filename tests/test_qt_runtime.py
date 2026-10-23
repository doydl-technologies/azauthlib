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

"""Check the installed Qt binding's reference accounting and normal interpreter exit."""

import json
import platform
import subprocess
import sys

import pytest

PROBE = """
import json
import sys

from PySide6.QtCore import QObject

obj = QObject()
method = obj.setObjectName
for _ in range(10):
    method("warmup")
before = sys.getrefcount(None)
for _ in range(1000):
    method("probe")
after = sys.getrefcount(None)
print(json.dumps({"delta": after - before}), flush=True)
"""


@pytest.mark.skipif(
    platform.python_implementation() != "CPython", reason="CPython reference counts"
)
def test_qt_void_calls_preserve_none_and_exit_cleanly():
    # The child must exit normally: an in-process check cannot observe a crash
    # during native-extension finalization after pytest has printed its verdict.
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["delta"] >= 0
