#!/usr/bin/env python3
"""
Scan a project's source code for HIPAA-relevant patterns.

Emits a JSON facts file consumed by rules_engine.py.

Detects:
  - PHI identifier patterns inside log statements
  - PHI identifiers in URL construction
  - Disabled TLS verification
  - Plaintext http:// to non-localhost
  - Wildcard CORS
  - Hardcoded secrets
  - Audit-logging evidence
  - Log scrubbers
  - Session timeout configs
  - PHI patterns in test fixtures / seed files
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".rb", ".go", ".java", ".kt", ".swift", ".m", ".mm",
    ".php", ".cs", ".scala", ".rs", ".dart", ".vue", ".svelte",
}
FIXTURE_HINTS = ("fixture", "seed", "factories", "mocks", "stub", "test_data", "sample")
SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__",
    "dist", "build", ".next", ".nuxt", "out", "target",
    ".idea", ".vscode", "coverage", ".pytest_cache",
}

PHI_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ssn_field": re.compile(r"\b(ssn|social_security|socialSecurity)\b", re.I),
    "mrn_field": re.compile(r"\b(mrn|medical_record|medicalRecord|patient_id|patientId)\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "dob_field": re.compile(r"\b(dob|date_of_birth|dateOfBirth|birthdate|birth_date)\b"),
    "address_field": re.compile(r"\b(street_address|streetAddress|zip_code|zipCode|address_line)\b"),
}

LOG_CALL = re.compile(
    r"""(?ix)
    \b(
        console\.(?:log|info|warn|error|debug) |
        logger?\.(?:log|info|warn|error|debug|trace|fatal) |
        log\.(?:info|warn|error|debug|trace|fatal) |
        print(?:ln)?\s*\( |
        printf\s*\( |
        fmt\.(?:Println|Printf|Print) |
        NSLog\s*\( |
        Log\.(?:d|i|w|e|v)
    )
    """
)

URL_CONSTRUCT = re.compile(
    r"""(?ix)
    (?:
        \"https?://[^\"\s]+ |
        `https?://[^`]+ |
        \'https?://[^\'\s]+ |
        url\s*[:=]\s* |
        href\s*[:=]\s* |
        redirect\s*\( |
        Location\s*[:=]
    )
    """
)

TLS_DISABLED = re.compile(
    r"""(?ix)
    (
        verify\s*=\s*False |
        rejectUnauthorized\s*:\s*false |
        InsecureSkipVerify\s*:\s*true |
        ALLOW_INVALID_CERTIFICATES |
        NSAllowsArbitraryLoads\s*[:=]\s*(?:true|YES) |
        TrustAllCerts |
        HostnameVerifier\s*\(\s*\)\s*->.*true |
        ServerCertificateValidationCallback
    )
    """
)

PLAINTEXT_HTTP = re.compile(
    r"""http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|::1)[A-Za-z0-9.\-]+""",
    re.IGNORECASE,
)

WILDCARD_CORS = re.compile(
    r"""(?ix)
    Access-Control-Allow-Origin\s*[:=]\s*[\"\']\*[\"\']  |
    origin\s*[:=]\s*[\"\']\*[\"\'] |
    cors\s*\(\s*\{?\s*origin\s*:\s*[\"\']\*[\"\']
    """
)

HARDCODED_SECRET = re.compile(
    r"""(?ix)
    (?:api[_-]?key|secret|token|password|passwd|pwd|access[_-]?key|private[_-]?key)
    \s*[:=]\s*
    [\"\']
    (?!\s*$|process\.env|os\.environ|ENV\[|\$\{|\<|\{\{)
    (?P<val>[A-Za-z0-9_\-\+/=]{12,})
    [\"\']
    """
)

AUDIT_LOG_EVIDENCE = re.compile(
    r"""(?ix)
    (
        audit[_-]?log |
        audit[_-]?trail |
        auditLog\s*\( |
        logAccess\s*\( |
        AuditLogger |
        record_access |
        recordPhiAccess
    )
    """
)

LOG_SCRUBBER = re.compile(
    r"""(?ix)
    (
        pino[-_]?noir |
        bunyan[-_]?redact |
        structlog\.processors |
        beforeSend |
        scrubFields |
        redactKeys |
        sanitize[_-]?logs |
        log[_-]?redactor
    )
    """
)

SESSION_TIMEOUT = re.compile(
    r"""(?ix)
    (
        session(?:Timeout|Idle|MaxAge|Lifetime) |
        idle[_-]?timeout |
        max[_-]?age |
        auto[_-]?logoff
    )
    \s*[:=]\s*
    (?P<val>\d+)
    """
)


@dataclass
class Counts:
    phi_in_logs_count: int = 0
    phi_in_urls_count: int = 0
    plaintext_http_count: int = 0
    tls_verify_disabled: bool = False
    wildcard_cors_count: int = 0
    hardcoded_secrets_count: int = 0
    audit_log_evidence: bool = False
    log_scrubber_present: bool = False
    session_timeout_configured: bool = False
    phi_in_fixtures_count: int = 0
    samples: dict[str, list[str]] = field(default_factory=dict)

    def add_sample(self, key: str, sample: str) -> None:
        self.samples.setdefault(key, [])
        if len(self.samples[key]) < 8 and sample not in self.samples[key]:
            self.samples[key].append(sample)


def walk_sources(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in SOURCE_EXTS:
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        yield path


def phi_pattern_hit(text: str) -> bool:
    for pat in PHI_PATTERNS.values():
        if pat.search(text):
            return True
    return False


def scan_file(path: Path, counts: Counts, is_fixture: bool) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    for lineno, line in enumerate(text.splitlines(), 1):
        loc = f"{path}:{lineno}"

        if LOG_CALL.search(line) and phi_pattern_hit(line):
            counts.phi_in_logs_count += 1
            counts.add_sample("phi_in_logs", f"{loc} — {line.strip()[:140]}")

        if URL_CONSTRUCT.search(line) and phi_pattern_hit(line):
            counts.phi_in_urls_count += 1
            counts.add_sample("phi_in_urls", f"{loc} — {line.strip()[:140]}")

        if TLS_DISABLED.search(line):
            counts.tls_verify_disabled = True
            counts.add_sample("tls_verify_disabled", f"{loc} — {line.strip()[:140]}")

        for m in PLAINTEXT_HTTP.finditer(line):
            counts.plaintext_http_count += 1
            counts.add_sample("plaintext_http", f"{loc} — {m.group(0)[:140]}")

        if WILDCARD_CORS.search(line):
            counts.wildcard_cors_count += 1
            counts.add_sample("wildcard_cors", f"{loc} — {line.strip()[:140]}")

        for m in HARDCODED_SECRET.finditer(line):
            val = m.group("val")
            if val.lower() in {"changeme", "your_key", "your-key", "xxxxxxxxxxxxxxxxxxxx", "placeholder", "examplekey"}:
                continue
            counts.hardcoded_secrets_count += 1
            counts.add_sample("hardcoded_secrets", f"{loc} — {m.group(0)[:140]}")

        if AUDIT_LOG_EVIDENCE.search(line):
            counts.audit_log_evidence = True

        if LOG_SCRUBBER.search(line):
            counts.log_scrubber_present = True

        if SESSION_TIMEOUT.search(line):
            counts.session_timeout_configured = True

        if is_fixture and phi_pattern_hit(line):
            counts.phi_in_fixtures_count += 1
            counts.add_sample("phi_in_fixtures", f"{loc} — {line.strip()[:140]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.project.resolve()
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 2

    counts = Counts()
    files_scanned = 0
    for path in walk_sources(root):
        is_fixture = any(h in str(path).lower() for h in FIXTURE_HINTS)
        scan_file(path, counts, is_fixture)
        files_scanned += 1

    facts = {
        "project_path": str(root),
        "files_scanned": files_scanned,
        "code": {
            "phi_in_logs_count": counts.phi_in_logs_count,
            "phi_in_urls_count": counts.phi_in_urls_count,
            "plaintext_http_count": counts.plaintext_http_count,
            "tls_verify_disabled": counts.tls_verify_disabled,
            "wildcard_cors_count": counts.wildcard_cors_count,
            "hardcoded_secrets_count": counts.hardcoded_secrets_count,
            "audit_log_evidence": counts.audit_log_evidence,
            "log_scrubber_present": counts.log_scrubber_present,
            "session_timeout_configured": counts.session_timeout_configured,
            "phi_in_fixtures_count": counts.phi_in_fixtures_count,
            "samples": counts.samples,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(facts, indent=2))
    print(f"scan_code: {files_scanned} files → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
