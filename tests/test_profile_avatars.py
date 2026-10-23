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

"""Avatar selection is visual metadata with a restricted, packaged SVG catalog."""

import json
import time
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QObject, QSize

from azauthlib import credentials, profiles
from azauthlib.gui.connections import ConnectionManagerController
from azauthlib.gui.svg_images import ProfileAvatarImageProvider
from azauthlib.profile_avatars import EXCLUDED_PROFILE_AVATARS, profile_avatar_names

ASSETS = Path(__file__).resolve().parents[1] / "src/azauthlib/assets"


class Resources:
    def path(self, category, *parts):
        assert category == "assets"
        return ASSETS.joinpath(*parts)


def test_catalog_contains_every_svg_except_the_six_menu_icons():
    directory = ASSETS / "icons/svg/third-party/profile-avatar"
    expected = {p.name for p in directory.glob("*.svg")} - EXCLUDED_PROFILE_AVATARS
    assert set(profile_avatar_names()) == expected
    assert len(expected) > 100
    assert profile_avatar_names() == tuple(sorted(expected))


def test_avatar_persists_per_profile_without_changing_authentication_or_selection():
    first = profiles.create_profile("First")
    second = profiles.create_profile("Second", select=False)
    credentials.save_configuration(
        profile=first,
        client_id="11111111-1111-1111-1111-111111111111",
        tenant_id="22222222-2222-2222-2222-222222222222",
        auth_method="device_code",
    )
    before = credentials.load_public_configuration(profile=first)
    artwork = profile_avatar_names()[0]
    saved = profiles.set_profile_avatar(first, artwork)
    assert saved.avatar == artwork
    assert profiles.resolve_profile(first).avatar == artwork
    assert profiles.resolve_profile(second).avatar == ""
    assert profiles.active_profile().id == first.id
    assert credentials.load_public_configuration(profile=first) == before
    assert profiles.rename_profile(first, "Renamed").avatar == artwork
    assert profiles.select_profile(second).avatar == ""
    assert profiles.select_profile(first).avatar == artwork
    assert profiles.set_profile_avatar(first, "").avatar == ""
    assert "avatar" not in json.loads(profiles._registry_path().read_text())["profiles"][0]


@pytest.mark.parametrize(
    "artwork",
    [
        *sorted(EXCLUDED_PROFILE_AVATARS),
        "../azure-a.svg",
        "https://example.com/icon.svg",
        "image.png",
        None,
    ],
)
def test_invalid_or_excluded_choices_cannot_be_saved_or_rendered(artwork):
    profile = profiles.create_profile("First")
    before = profiles._registry_path().read_bytes()
    with pytest.raises(ValueError):
        profiles.set_profile_avatar(profile, artwork)
    assert profiles._registry_path().read_bytes() == before
    if isinstance(artwork, str):
        provider = ProfileAvatarImageProvider(Resources())
        assert provider.requestImage(artwork, QSize(), QSize(64, 64)).isNull()


@pytest.mark.parametrize("artwork", ["missing.svg", "sql-server.svg", "../azure-a.svg", 123])
def test_unavailable_stored_artwork_falls_back_without_losing_the_profile(artwork):
    profile = profiles.create_profile("First")
    path = profiles._registry_path()
    registry = json.loads(path.read_text())
    registry["profiles"][0]["avatar"] = artwork
    path.write_text(json.dumps(registry))
    assert profiles.resolve_profile(profile).avatar == ""
    assert profiles.resolve_profile(profile).name == "First"


def test_controller_reloads_saved_artwork_and_prevents_edits_during_authentication():
    first = profiles.create_profile("First")
    second = profiles.create_profile("Second", select=False)
    parent = QObject()
    manager = ConnectionManagerController(parent)
    artwork = profile_avatar_names()[0]
    assert manager.avatarChoices[0] == ""
    assert manager.setAvatar(artwork)
    assert manager.editor["avatar"] == artwork
    manager.selectConnection(second.id)
    assert manager.editor["avatar"] == ""
    manager.selectConnection(first.id)
    assert manager.editor["avatar"] == artwork
    manager.beginEdit()
    assert manager.setAvatar("")
    assert manager.avatar == ""
    assert profiles.resolve_profile(first).avatar == artwork
    manager.cancelEdit()
    assert manager.avatar == artwork
    manager._busy = True
    assert not manager.setAvatar("")
    manager._busy = False
    assert profiles.resolve_profile(first).avatar == artwork
    restored = ConnectionManagerController(parent)
    assert restored.editor["avatar"] == artwork


def test_avatar_drafts_save_cancel_and_revert_without_resetting_the_editor():
    parent = QObject()
    manager = ConnectionManagerController(parent)
    artwork = profile_avatar_names()[0]
    client = "a8bf703b-a38a-4786-a4c1-96ea20531620"
    tenant = "91273e86-781d-4a9e-b3a1-e06c74d8a043"
    manager.beginAdd()
    assert manager.setAvatar(artwork)
    assert manager.avatar == artwork
    assert manager.connectionDraftChanged("", "", "", "", "interactive")
    assert not any(p.name == "Avatar draft" for p in profiles.list_profiles())
    assert manager.saveConnection("Avatar draft", tenant, client, "", "interactive")
    saved = profiles.resolve_profile(manager.selectedId)
    assert saved.avatar == artwork
    manager.beginEdit()
    editor = dict(manager.editor)
    assert manager.setAvatar("")
    assert manager.editor == editor  # No editorChanged/reset of other unsaved fields.
    assert manager.connectionDraftChanged(saved.name, tenant, client, "", "interactive")
    assert manager.setAvatar(artwork)
    assert not manager.connectionDraftChanged(saved.name, tenant, client, "", "interactive")
    assert manager.setAvatar("")
    manager.cancelEdit()
    assert manager.avatar == artwork
    manager.beginEdit()
    assert manager.setAvatar("")
    assert manager.saveConnection(saved.name, tenant, client, "", "interactive")
    assert profiles.resolve_profile(saved).avatar == ""


def test_failed_connection_save_rolls_back_avatar_draft(monkeypatch):
    from azauthlib.gui import connections

    parent = QObject()
    profile = profiles.create_profile("Saved avatar")
    manager = ConnectionManagerController(parent)
    manager.beginEdit()
    assert manager.setAvatar(profile_avatar_names()[0])

    def fail(**_):
        raise OSError("Simulated configuration write failure")

    monkeypatch.setattr(connections, "save_configuration", fail)
    assert not manager.saveConnection(
        profile.name,
        "91273e86-781d-4a9e-b3a1-e06c74d8a043",
        "a8bf703b-a38a-4786-a4c1-96ea20531620",
        "",
        "interactive",
    )
    assert profiles.resolve_profile(profile).avatar == ""


def test_avatar_write_failure_keeps_current_display_and_reports_failure(monkeypatch):
    profiles.create_profile("First")
    parent = QObject()
    manager = ConnectionManagerController(parent)

    def fail(*_):
        raise OSError("write failed")

    monkeypatch.setattr(profiles.os, "replace", fail)
    assert not manager.setAvatar(profile_avatar_names()[0])
    assert manager.editor["avatar"] == ""
    assert manager.statusKind == "error"


def test_avatar_renderer_preserves_colors_and_has_a_bounded_cache():
    provider = ProfileAvatarImageProvider(Resources())
    for name in profile_avatar_names()[:100]:
        image = provider.requestImage(name, QSize(), QSize(48, 48))
        assert not image.isNull(), name
        assert any(image.pixelColor(x, y).alpha() for x in range(48) for y in range(48)), name
    assert len(provider._cache) <= 96


def test_entire_gallery_is_preloaded_once_and_reused_at_tile_sizes(monkeypatch):
    provider = ProfileAvatarImageProvider(Resources())
    progress = []
    assert provider.preload(lambda done, total: progress.append((done, total))) == len(
        profile_avatar_names()
    )
    assert progress[-1] == (len(profile_avatar_names()), len(profile_avatar_names()))
    assert len(provider._previews) == len(profile_avatar_names())
    assert sum(image.sizeInBytes() for image in provider._previews.values()) < 48 * 1024**2

    def unexpected_render(*_):
        pytest.fail("Scrolling after preload must reuse the warm thumbnail")

    monkeypatch.setattr(provider, "_render", unexpected_render)
    for name in reversed(profile_avatar_names()):
        size = QSize()
        assert provider.requestImage(name, size, QSize(84, 84)).size() == QSize(84, 84)
        assert size == QSize(84, 84)
    assert provider.preload() == len(profile_avatar_names())


def test_preload_is_bounded_cancellable_and_tolerates_individual_bad_artwork(monkeypatch):
    from azauthlib.gui import svg_images

    monkeypatch.setattr(svg_images, "_AVATAR_PREVIEW_LIMIT", 3)
    provider = ProfileAvatarImageProvider(Resources())
    original_render = provider._render
    first = next(iter(provider._paths))

    def damaged_asset(path, width, height):
        if path.name == first:
            raise ValueError("damaged optional SVG")
        return original_render(path, width, height)

    monkeypatch.setattr(provider, "_render", damaged_asset)
    assert provider.preload() == 2
    assert first not in provider._previews
    before = dict(provider._previews)
    assert provider.preload(cancelled=lambda: True) == 0
    assert provider._previews == before
    monkeypatch.setattr(provider, "_render", original_render)
    for name in profile_avatar_names()[:6]:
        assert not provider.requestImage(name, QSize(), QSize(128, 128)).isNull()
    assert len(provider._previews) == 3


def test_startup_and_interface_share_the_same_registered_provider():
    from azauthlib.gui.svg_images import ensure_image_providers

    class Engine(QObject):
        providers = {}

        def rootContext(self):
            return self

        def setContextProperty(self, name, value):
            assert name == "accentPalette"
            self.palette = value

        def imageProvider(self, name):
            return self.providers.get(name)

        def addImageProvider(self, name, provider):
            assert name not in self.providers
            self.providers[name] = provider

    engine = Engine()
    first = ensure_image_providers(engine, Resources())
    assert ensure_image_providers(engine, Resources()) is first
    assert set(engine.providers) == {
        "providerlogos",
        "profileavatars",
        "actionicons",
        "connectionanimation",
        "accentart",
    }


def test_async_tile_loading_uses_neutral_placeholder_and_never_previous_artwork(monkeypatch):
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QGuiApplication, QImage
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
    from PySide6.QtQuick import QQuickImageProvider, QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    if QGuiApplication.instance() is None:
        QQuickStyle.setStyle("Basic")
    app = QGuiApplication.instance() or QGuiApplication([])
    release = Event()

    class DelayedProvider(QQuickImageProvider):
        def __init__(self):
            super().__init__(QQuickImageProvider.Image)

        def requestImage(self, name, size, requestedSize):
            release.wait(3)
            image = QImage(128, 128, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.red if name == "one.svg" else Qt.green)
            return image

    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        assert predicate()

    engine = QQmlApplicationEngine()
    engine.addImageProvider("profileavatars", DelayedProvider())
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(ASSETS.parent / "gui/qml/components/ProfileAvatar.qml")),
    )
    item = component.createWithInitialProperties(
        {"objectName": "tile", "width": 42, "height": 42, "avatarId": "one.svg"}
    )
    assert item is not None, component.errors()
    window = QQuickWindow()
    item.setParentItem(window.contentItem())
    window.show()
    try:
        artwork = item.findChild(QObject, "tileArtwork")
        placeholder = item.findChild(QObject, "tileLoadingPlaceholder")
        plug = item.findChild(QObject, "tileDefaultPlug")
        assert item.property("loading") and placeholder.isVisible() and not plug.isVisible()
        assert not artwork.isVisible() and not artwork.property("retainWhileLoading")
        release.set()
        wait_for(lambda: not item.property("loading"))
        assert artwork.isVisible() and not placeholder.isVisible()
        release.clear()
        item.setProperty("avatarId", "two.svg")
        assert item.property("loading") and placeholder.isVisible()
        assert not artwork.isVisible() and not plug.isVisible()
        release.set()
        wait_for(lambda: not item.property("loading"))
        item.setProperty("avatarId", "")
        assert plug.isVisible() and not placeholder.isVisible() and not artwork.isVisible()
    finally:
        release.set()
        window.hide()
        item.setParentItem(None)
        item.deleteLater()
        app.processEvents()
