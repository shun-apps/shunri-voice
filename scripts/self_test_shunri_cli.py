#!/usr/bin/env python3
from __future__ import annotations

import http.client
from unittest.mock import patch

import shunri_cli


class HealthyResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def main() -> int:
    with patch(
        "shunri_cli.urllib.request.urlopen",
        side_effect=ConnectionResetError(54, "Connection reset by peer"),
    ):
        assert shunri_cli.server_is_healthy() is False

    with patch(
        "shunri_cli.urllib.request.urlopen",
        side_effect=http.client.RemoteDisconnected("Remote end closed connection"),
    ):
        assert shunri_cli.server_is_healthy() is False

    with patch(
        "shunri_cli.urllib.request.urlopen",
        side_effect=TimeoutError("timed out"),
    ):
        assert shunri_cli.server_is_healthy() is False

    with patch(
        "shunri_cli.urllib.request.urlopen",
        return_value=HealthyResponse(),
    ):
        assert shunri_cli.server_is_healthy() is True

    print("shunri-cli-self-test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
