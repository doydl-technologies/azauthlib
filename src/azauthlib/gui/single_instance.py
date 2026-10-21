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

"""Enforce one desktop instance per user configuration directory.

The OS file lock is authoritative. IPC is only an activation channel, never a
reason to bypass the lock or open another UI when an existing process is busy.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from . import platform_integration
from .gui_utils import enforce_single_instance, on_exit


class SingleInstance(QObject):
    activationRequested = Signal()

    def __init__(self, lockfile, parent=None):
        super().__init__(parent)
        self.lockfile = Path(lockfile)
        identity = os.path.normcase(str(self.lockfile.resolve()))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        self.server_name = "doydl-azauthlib-" + digest
        self.forwarded = False
        self._lock = None
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._accept)
        self._clients = set()

    def start(self, *, timeout_ms=2000):
        """Return True for the owner, False after forwarding a repeated launch.

        Bounded waits run only in the secondary process, before it creates any
        window or loads profiles, credentials, or assets.
        The owner's message handling is entirely event-driven.
        """
        if self._lock is not None:
            return True
        deadline = monotonic() + timeout_ms / 1000
        while True:
            self._lock = enforce_single_instance(self.lockfile)
            if self._lock is not None:
                # Only the lock owner may remove a stale IPC endpoint.
                QLocalServer.removeServer(self.server_name)
                if not self._server.listen(self.server_name):
                    self.close()
                    raise OSError("Unable to open the azauthlib activation channel")
                return True
            if self._forward(deadline):
                self.forwarded = True
                return False
            if monotonic() >= deadline:
                return False  # A busy or incompatible owner must not create a second window.
            QThread.msleep(20)

    def _forward(self, deadline):
        socket = QLocalSocket()

        def wait_budget():
            return max(1, min(150, int((deadline - monotonic()) * 1000)))

        def read_line():
            while not socket.canReadLine() and monotonic() < deadline:
                if not socket.waitForReadyRead(wait_budget()):
                    return b""
            if socket.bytesAvailable() > 64:
                return b""
            return bytes(socket.readLine()).strip()

        try:
            socket.connectToServer(self.server_name)
            if not socket.waitForConnected(wait_budget()):
                return False
            socket.write(b"hello\n")
            socket.flush()
            pid = read_line()
            if not pid.isdigit() or not 0 < int(pid) <= 0xFFFFFFFF:
                return False
            # Transfer Windows foreground permission to the owner before activation.
            platform_integration.allow_foreground_activation(int(pid))
            socket.write(b"activate\n")
            socket.flush()
            return read_line() == b"ok"
        finally:
            socket.abort()

    @Slot()
    def _accept(self):
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            self._clients.add(socket)
            socket.setReadBufferSize(128)
            socket.readyRead.connect(self._client_ready)
            socket.disconnected.connect(self._client_closed)
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(socket.abort)
            timer.start(3000)
            self._read(socket)  # Read data buffered before the readyRead handler was connected.

    @Slot()
    def _client_ready(self):
        self._read(self.sender())

    def _read(self, socket):
        if socket.bytesAvailable() > 64:
            socket.abort()
            return
        while socket.canReadLine():
            message = bytes(socket.readLine()).strip()
            if message == b"hello":
                socket.write(str(os.getpid()).encode("ascii") + b"\n")
                socket.flush()
            elif message == b"activate":
                socket.write(b"ok\n")
                socket.flush()
                self.activationRequested.emit()
                socket.disconnectFromServer()
                return
            else:
                socket.abort()
                return

    @Slot()
    def _client_closed(self):
        socket = self.sender()
        self._clients.discard(socket)
        socket.deleteLater()

    def close(self):
        for socket in tuple(self._clients):
            socket.abort()
        self._clients.clear()
        self._server.close()
        lock, self._lock = self._lock, None
        on_exit(lock)
