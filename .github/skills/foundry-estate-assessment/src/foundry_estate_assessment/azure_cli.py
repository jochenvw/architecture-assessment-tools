"""Azure access abstraction.

Everything the scanner learns about Azure flows through :class:`AzureClient`.
The client shells out to the Azure CLI through an injectable
:class:`CommandRunner`, which makes the whole scanner testable offline via
:class:`FixtureCommandRunner`.

No shell strings are constructed: every command is an argument list passed to
``subprocess`` without ``shell=True``. Errors are classified into typed
exceptions so collectors can map them to precise task states.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from . import api_versions


class AzureError(Exception):
    """Base class for Azure access errors."""


class AuthenticationError(AzureError):
    """The CLI is not logged in / token acquisition failed."""


class AuthorizationError(AzureError):
    """The identity lacks permission (maps to BLOCKED_PERMISSION)."""


class NetworkError(AzureError):
    """A network / data-plane reachability failure (maps to BLOCKED_NETWORK)."""


class ThrottlingError(AzureError):
    """The service throttled the request (429 / TooManyRequests)."""

    def __init__(self, message: str, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class UnsupportedApiError(AzureError):
    """The API version or resource type is unsupported (maps to UNSUPPORTED)."""


class MalformedResponseError(AzureError):
    """The CLI returned output that could not be parsed as JSON."""


@dataclass
class CommandResult:
    args: list[str]
    exit_code: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    """Abstraction over process execution so Azure calls are injectable."""

    def run(self, args: list[str], timeout: Optional[float] = None) -> CommandResult:
        ...


class SubprocessCommandRunner:
    """Runs commands via ``subprocess`` using argument arrays (no shell)."""

    def __init__(self, az_path: str = "az") -> None:
        self._az_path = az_path

    def run(self, args: list[str], timeout: Optional[float] = None) -> CommandResult:
        # ``az`` is a batch file on Windows; resolve through the shell resolver
        # only by name, never by concatenating untrusted values.
        cmd = [self._az_path, *args]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError as exc:  # pragma: no cover - environment dependent
            raise AzureError(f"Azure CLI executable not found: {self._az_path}") from exc
        except subprocess.TimeoutExpired as exc:  # pragma: no cover
            raise NetworkError(f"Command timed out: az {' '.join(args)}") from exc
        return CommandResult(cmd, completed.returncode, completed.stdout or "", completed.stderr or "")


def _classify_error(stderr: str, exit_code: int) -> AzureError:
    lowered = stderr.lower()
    if any(m in lowered for m in ("please run 'az login'", "az login", "no subscription found", "authenticationfailed", "token", "credential")):
        if "login" in lowered or "authenticationfailed" in lowered:
            return AuthenticationError(stderr.strip() or "authentication failed")
    if any(m in lowered for m in ("authorizationfailed", "does not have authorization", "forbidden", "insufficient privileges", "accessdenied", "(403)")):
        return AuthorizationError(stderr.strip() or "authorization failed")
    if any(m in lowered for m in ("toomanyrequests", "throttl", "(429)", "rate limit")):
        return ThrottlingError(stderr.strip() or "throttled")
    if any(m in lowered for m in ("noregisteredproviderfound", "no registered resource provider", "unsupported api", "invalidapiversion", "the resource type could not be found", "badrequest api version")):
        return UnsupportedApiError(stderr.strip() or "unsupported api")
    if any(m in lowered for m in ("could not resolve host", "connection", "timed out", "network", "dns", "getaddrinfo")):
        return NetworkError(stderr.strip() or "network error")
    return AzureError(stderr.strip() or f"az exited with code {exit_code}")


class AzureClient:
    """High-level, JSON-returning Azure operations used by collectors."""

    def __init__(self, runner: CommandRunner, default_timeout: float = 120.0) -> None:
        self._runner = runner
        self._timeout = default_timeout

    # -- primitives -------------------------------------------------------
    def _az_json(self, args: list[str]) -> Any:
        result = self._runner.run([*args, "--output", "json"], timeout=self._timeout)
        if result.exit_code != 0:
            raise _classify_error(result.stderr, result.exit_code)
        text = result.stdout.strip()
        if text == "":
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise MalformedResponseError(f"Non-JSON output from: az {' '.join(args)}") from exc

    # -- identity / scope -------------------------------------------------
    def account_show(self) -> dict[str, Any]:
        return self._az_json(["account", "show"]) or {}

    def cli_version(self) -> str:
        data = self._az_json(["version"]) or {}
        return str(data.get("azure-cli", "unknown"))

    def list_subscriptions(self) -> list[dict[str, Any]]:
        data = self._az_json(["account", "list", "--all"]) or []
        return list(data)

    # -- resource graph ---------------------------------------------------
    def graph_query(self, query: str, subscriptions: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Run a Resource Graph query, following ``--skip-token`` pagination."""
        results: list[dict[str, Any]] = []
        skip_token: Optional[str] = None
        while True:
            args = ["graph", "query", "-q", query, "--first", "1000"]
            if subscriptions:
                args += ["--subscriptions", *subscriptions]
            if skip_token:
                args += ["--skip-token", skip_token]
            payload = self._az_json(args)
            if payload is None:
                break
            if isinstance(payload, list):
                results.extend(payload)
                break
            results.extend(payload.get("data", []) or [])
            skip_token = payload.get("skip_token") or payload.get("skipToken")
            if not skip_token:
                break
        return results

    # -- ARM REST ---------------------------------------------------------
    def rest_get(self, resource_id: str, api_version: str, sub_path: str = "") -> Any:
        """GET an ARM resource (or child collection), following ``nextLink``."""
        url = f"https://management.azure.com{resource_id}{sub_path}?api-version={api_version}"
        return self._rest_get_paged(url)

    def _rest_get_paged(self, url: str) -> Any:
        first = self._az_json(["rest", "--method", "get", "--url", url])
        if not isinstance(first, dict) or "value" not in first:
            return first
        values = list(first.get("value") or [])
        next_link = first.get("nextLink") or first.get("@odata.nextLink")
        guard = 0
        while next_link and guard < 100:
            guard += 1
            page = self._az_json(["rest", "--method", "get", "--url", next_link])
            if not isinstance(page, dict):
                break
            values.extend(page.get("value") or [])
            next_link = page.get("nextLink") or page.get("@odata.nextLink")
        return {"value": values}

    def rest_get_url(self, url: str) -> Any:
        return self._rest_get_paged(url)


class FixtureCommandRunner:
    """A :class:`CommandRunner` that serves canned responses from a directory.

    The fixture directory contains an ``estate.json`` file with three sections:

    * ``subscriptions`` -- list returned by ``az account list``
    * ``account`` / ``version`` -- identity + CLI version stubs
    * ``graph`` -- list of graph responses, each ``{"match": <substr>, "data": [...]}}``
    * ``rest`` -- mapping of URL-substring -> response object

    Commands that are not matched return an empty JSON result, letting
    collectors record ``UNKNOWN`` rather than crash. This mirrors real-world
    partial coverage and keeps fixtures small.
    """

    def __init__(self, fixture_dir: Path) -> None:
        self._dir = Path(fixture_dir)
        with (self._dir / "estate.json").open("r", encoding="utf-8") as handle:
            self._estate: dict[str, Any] = json.load(handle)

    def run(self, args: list[str], timeout: Optional[float] = None) -> CommandResult:
        payload = self._dispatch([a for a in args if a != "--output" and a != "json"])
        stdout = "" if payload is None else json.dumps(payload)
        return CommandResult(["az", *args], 0, stdout, "")

    def _dispatch(self, args: list[str]) -> Any:
        if args[:2] == ["account", "show"]:
            return self._estate.get("account", {"tenantId": "fixture-tenant", "user": {"name": "fixture@example.com", "type": "user"}})
        if args[:1] == ["version"]:
            return self._estate.get("version", {"azure-cli": "fixture"})
        if args[:2] == ["account", "list"]:
            return self._estate.get("subscriptions", [])
        if args[:2] == ["graph", "query"]:
            query = _flag_value(args, "-q") or ""
            for entry in self._estate.get("graph", []):
                if entry.get("match", "") in query:
                    return {"data": entry.get("data", []), "skip_token": None}
            return {"data": [], "skip_token": None}
        if args[:1] == ["rest"]:
            url = _flag_value(args, "--url") or ""
            rest = self._estate.get("rest", {})
            # Longest-matching key wins for deterministic resolution.
            best: Optional[str] = None
            for key in rest:
                if key in url and (best is None or len(key) > len(best)):
                    best = key
            if best is not None:
                return rest[best]
            return {"value": []}
        return None


def _flag_value(args: list[str], flag: str) -> Optional[str]:
    for index, token in enumerate(args):
        if token == flag and index + 1 < len(args):
            return args[index + 1]
    return None


def build_client(fixture_dir: Optional[Path] = None, az_path: str = "az") -> AzureClient:
    """Construct an :class:`AzureClient` for real or fixture execution."""
    if fixture_dir is not None:
        return AzureClient(FixtureCommandRunner(fixture_dir))
    return AzureClient(SubprocessCommandRunner(az_path))
