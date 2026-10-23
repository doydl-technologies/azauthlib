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

"""Provider artwork resolves through package-relative paths and renders intact."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSize

from azauthlib.gui.svg_images import (
    ACTION_ICON_PATHS,
    PROVIDER_LOGO_PATHS,
    ActionIconImageProvider,
    ProviderLogoImageProvider,
)

ASSETS = Path(__file__).resolve().parents[1] / "src/azauthlib/assets"


class Resources:
    def path(self, category, *parts):
        assert category == "assets"
        return ASSETS.joinpath(*parts)


@pytest.mark.parametrize("name", PROVIDER_LOGO_PATHS)
def test_provider_logo_exists_and_renders(name):
    provider = ProviderLogoImageProvider(Resources())
    assert provider._paths[name] == ASSETS.joinpath(*PROVIDER_LOGO_PATHS[name], name)
    assert provider._paths[name].is_file()
    image = provider.requestImage(name, QSize(), QSize(64, 64))
    assert not image.isNull()
    assert any(image.pixelColor(x, y).alpha() for x in range(64) for y in range(64))


def test_old_names_and_arbitrary_paths_are_not_loaded():
    provider = ProviderLogoImageProvider(Resources())
    for name in (
        "icon-azure-key-vault.svg",
        "icon-azure-sql-database.svg",
        "icon-azure-storage-account.svg",
        "../subscriptions.svg",
    ):
        assert provider.requestImage(name, QSize(), QSize(64, 64)).isNull()


def test_white_lockup_is_available_at_new_location():
    path = ASSETS / "logo/svg/third-party/logo-microsoft-white-lockup.svg"
    assert path.is_file()
    assert not ProviderLogoImageProvider._render(path, 128, 64).isNull()


@pytest.mark.parametrize("name", ACTION_ICON_PATHS)
def test_action_icons_render_original_colors_without_modifying_assets(name):
    provider = ActionIconImageProvider(Resources())
    path = provider._paths[name]
    original = path.read_bytes()
    image = provider.requestImage(name, QSize(), QSize(96, 96))
    assert not image.isNull()
    assert any(
        image.pixelColor(x, y).alpha()
        and (
            image.pixelColor(x, y).saturation() > 40
            or image.pixelColor(x, y).name() in {"#cccccc", "#ffffff"}
        )
        for x in range(96)
        for y in range(96)
    )
    assert path.read_bytes() == original
    assert provider.requestImage("../" + name, QSize(), QSize(96, 96)).isNull()


def test_action_checkmark_retains_transparent_cutout_and_saved_mint_color():
    provider = ActionIconImageProvider(Resources())
    image = provider.requestImage(
        "Multicolor-Filled-Mint-Green-Transparent-circle-check.svg", QSize(), QSize(240, 240)
    )
    assert image.pixelColor(120, 60).name() == "#5bdcaf"
    assert image.pixelColor(90, 135).alpha() == 0
    assert image.pixelColor(0, 0).alpha() == 0


def test_action_plus_retains_saved_sky_blue_strokes():
    provider = ActionIconImageProvider(Resources())
    image = provider.requestImage(
        "Monocolor-Filled-Sky-Blue-circle-plus.svg", QSize(), QSize(240, 240)
    )
    assert image.pixelColor(120, 120).name() == "#38a8ff"
    assert image.pixelColor(90, 90).alpha() == 0


def test_inactive_radio_icon_retains_original_gray_color_and_clear_ring():
    provider = ActionIconImageProvider(Resources())
    image = provider.requestImage(
        "Monocolor-Rounded-Filled-Light-Gray-Radio-Button-Checked.svg", QSize(), QSize(240, 240)
    )
    assert image.pixelColor(120, 120).name() == "#cccccc"
    assert image.pixelColor(120, 25).name() == "#cccccc"
    assert image.pixelColor(120, 37).alpha() == 0
