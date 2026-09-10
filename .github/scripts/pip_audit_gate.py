"""Turn a pip-audit JSON report into a pass/fail decision based on advisory severity.

pip-audit reports advisory ids with no severity attached, so a plain non-zero exit would fail the
build on a low-severity advisory in a build-time dependency. Severity is resolved through the
GitHub advisory database, reached from the GHSA alias OSV records for the ids pip-audit returns,
and only high and critical stop the job. An advisory whose severity cannot be resolved is printed
and let through rather than guessed at.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BLOCKING_SEVERITIES = {"high", "critical"}
OSV_URL = "https://api.osv.dev/v1/vulns/{identifier}"
GITHUB_ADVISORY_URL = "https://api.github.com/advisories/{ghsa_id}"


def fetch_json(url: str) -> dict[str, object] | None:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def ghsa_id_of(identifier: str) -> str | None:
    if identifier.startswith("GHSA-"):
        return identifier
    entry = fetch_json(OSV_URL.format(identifier=identifier))
    aliases = entry.get("aliases", []) if entry else []
    if not isinstance(aliases, list):
        return None
    return next((alias for alias in aliases if str(alias).startswith("GHSA-")), None)


def severity_of(identifier: str, cache: dict[str, str | None]) -> str | None:
    ghsa_id = ghsa_id_of(identifier)
    if ghsa_id is None:
        return None
    if ghsa_id not in cache:
        advisory = fetch_json(GITHUB_ADVISORY_URL.format(ghsa_id=ghsa_id))
        severity = advisory.get("severity") if advisory else None
        cache[ghsa_id] = str(severity).lower() if severity else None
    return cache[ghsa_id]


def main(report_path: str) -> int:
    with open(report_path, encoding="utf-8") as report:
        dependencies = json.load(report)["dependencies"]

    cache: dict[str, str | None] = {}
    seen: set[tuple[str, str]] = set()
    blocking: list[str] = []

    for dependency in dependencies:
        for vulnerability in dependency.get("vulns", []):
            identifier = vulnerability["id"]
            if (dependency["name"], identifier) in seen:
                continue
            seen.add((dependency["name"], identifier))
            severity = severity_of(identifier, cache)
            line = (
                f"{dependency['name']} {dependency['version']}: {identifier} "
                f"[{severity or 'severity unknown'}] "
                f"fix: {', '.join(vulnerability.get('fix_versions') or ['none published'])}"
            )
            print(line)
            if severity in BLOCKING_SEVERITIES:
                blocking.append(line)

    if not blocking:
        print("\nNo high or critical advisory.")
        return 0

    print(f"\n{len(blocking)} high or critical advisory(-ies):")
    for line in blocking:
        print(line)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
