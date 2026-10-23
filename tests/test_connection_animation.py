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

"""Animation SVG parsing rejects declarations and unsupported encodings."""

import pytest

from azauthlib.gui.connection_animation import animation_svg


@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE svg [<!ENTITY external SYSTEM "file:///not-read">]>',
        '<!ENTITY external SYSTEM "file:///not-read">',
        "<!doctype svg>",
    ],
)
def test_animation_rejects_dtds_and_entities(tmp_path, declaration):
    path = tmp_path / "artwork.svg"
    path.write_text(declaration + '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="DTDs/entities"):
        animation_svg(path, "connected")


def test_animation_does_not_accept_utf16_encoded_declarations(tmp_path):
    path = tmp_path / "artwork.svg"
    path.write_text("<!DOCTYPE svg><svg/>", encoding="utf-16")
    with pytest.raises(UnicodeError):
        animation_svg(path, "connected")


def test_animation_preserves_utf8_artwork(tmp_path):
    path = tmp_path / "artwork.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><title>Connect →</title>'
        '<path fill="#abcdef" d="M0 0h1v1z"/></svg>',
        encoding="utf-8-sig",
    )
    result = animation_svg(path, "connected")
    assert 'viewBox="0 0 1254 1254"' in result
    assert 'fill="#abcdef"' in result
    assert "Connect →" in result
