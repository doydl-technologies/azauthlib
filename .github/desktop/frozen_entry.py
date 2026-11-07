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

"""Standalone entry point, including an explicit isolated native smoke-check mode."""

import os
import sys
from pathlib import Path


def main():
    if sys.platform.startswith("linux"):
        # Keep frozen Linux GUI/render callbacks on one thread; OpenGL stays active.
        os.environ.setdefault("QSG_RENDER_LOOP", "basic")
    if len(sys.argv) > 1 and sys.argv[1] == "--desktop-setup":
        from azauthlib.gui.desktop_setup import main as setup

        return setup(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "--desktop-setup-self-check":
        import _azauthlib_setup_smoke

        return _azauthlib_setup_smoke.main(sys.argv[2:])
    if len(sys.argv) == 3 and sys.argv[1] == "--desktop-self-check":
        artifacts = Path(sys.argv[2]).resolve()
        artifacts.mkdir(parents=True, exist_ok=True)
        # Windowed Windows builds have no console streams. Preserve diagnostics
        # in the caller's explicit test folder, never the user's configuration.
        with (artifacts / "frozen-output.log").open("w", encoding="utf-8") as stream:
            sys.stdout = sys.stderr = stream
            import _azauthlib_desktop_smoke

            return _azauthlib_desktop_smoke.main(
                ["--installed", sys._MEIPASS, "--artifacts", str(artifacts)]
            )
    from azauthlib.gui.config_app import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
