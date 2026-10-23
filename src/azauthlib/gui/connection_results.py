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

"""Non-sensitive test outcomes bound to credentials by a keyring-backed HMAC."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from contextlib import suppress

from .. import credentials, profiles
from ..appdata import ensure_private_directory
from ..certificates import CertificateError, file_identity

_SERVICE = credentials.KEYRING_SERVICE + ".connection-tests"
_ACCOUNT = "fingerprint-key"


class ConnectionResults:
    def __init__(self):
        self._key = None
        self._persistent_key = False
        self._volatile = {}

    @staticmethod
    def path():
        return profiles.get_config_dir(create=False) / "connection-test-results.json"

    def _read(self):
        try:
            path = self.path()
            if path.stat().st_size > 1_000_000:
                return {}
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") == 1 and isinstance(data.get("profiles"), dict):
                return data["profiles"]
        except (OSError, ValueError, AttributeError, RecursionError):
            pass
        return {}

    def _get_key(self, create):
        if self._key is not None:
            return self._key
        try:
            encoded = credentials.keyring.get_password(_SERVICE, _ACCOUNT)
            if encoded:
                key = base64.b64decode(encoded, validate=True)
                if len(key) == 32:
                    self._key, self._persistent_key = key, True
                    return key
        except Exception:
            self._persistent_key = False
        if not create:
            return None
        self._key = secrets.token_bytes(32)
        try:
            credentials.keyring.set_password(
                _SERVICE, _ACCOUNT, base64.b64encode(self._key).decode("ascii")
            )
            self._persistent_key = True
        except Exception:
            # Authentication still works if only history storage is unavailable.
            # Keep the result for this session instead of writing an unverifiable record.
            self._persistent_key = False
        return self._key

    def fingerprint(self, values, *, create=False):
        key = self._get_key(create)
        if key is None:
            return None
        secret = None
        certificate_identity = None
        if values.get("auth_method") == "client_certificate":
            try:
                spec = values.get("certificate") or {}
                certificate_identity = [spec, file_identity(spec)]
            except CertificateError:
                return None
        if values.get("auth_method") == "client_credentials":
            if "_client_secret" in values:
                secret = values["_client_secret"]
            else:
                try:
                    secret = credentials.keyring.get_password(
                        credentials.KEYRING_SERVICE, values.get("client_id")
                    )
                except Exception:
                    return None
        payload = json.dumps(
            [
                values.get("tenant_id"),
                values.get("client_id"),
                values.get("auth_method"),
                values.get("authority"),
                secret,
                *([certificate_identity] if certificate_identity is not None else []),
            ],
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def state(self, profile_id, values):
        record = self._volatile.get(profile_id, self._read().get(profile_id))
        if not isinstance(record, dict) or record.get("result") not in ("passed", "failed"):
            return "untested"
        tag = self.fingerprint(values)
        saved = record.get("fingerprint")
        signature = record.get("signature")
        if (
            tag
            and isinstance(saved, str)
            and hmac.compare_digest(tag, saved)
            and isinstance(signature, str)
            and hmac.compare_digest(signature, self._signature(profile_id, record))
        ):
            return record["result"]
        return "untested"

    def _signature(self, profile_id, record):
        payload = json.dumps(
            [profile_id, record["fingerprint"], record["result"]], separators=(",", ":")
        ).encode("utf-8")
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def _write(self, records):
        target = self.path()
        ensure_private_directory(target.parent)
        descriptor, temporary = tempfile.mkstemp(prefix=".connection-tests-", dir=target.parent)
        try:
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump({"version": 1, "profiles": records}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except Exception:
            with suppress(FileNotFoundError):
                os.unlink(temporary)
            raise

    def remember(self, profile_id, tag, passed):
        if not tag:
            return
        record = {"fingerprint": tag, "result": "passed" if passed else "failed"}
        record["signature"] = self._signature(profile_id, record)
        self._volatile[profile_id] = record
        if self._persistent_key:
            try:
                records = self._read()
                records[profile_id] = record
                self._write(records)
            except OSError:
                pass

    def forget(self, profile_id):
        self._volatile.pop(profile_id, None)
        try:
            records = self._read()
            if profile_id in records:
                del records[profile_id]
                self._write(records)
        except OSError:
            pass
