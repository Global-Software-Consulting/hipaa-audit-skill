#!/usr/bin/env python3
"""
Scan infra config: Dockerfile, docker-compose, Terraform, k8s yaml, serverless,
.env, GitHub Actions. Emit facts about encryption, TLS, secrets-in-repo, log
retention hints, and manual-verification items.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__",
    "dist", "build", ".next", ".nuxt", "out", "target",
    ".idea", ".vscode", "coverage", ".pytest_cache",
}

INFRA_FILE_HINTS = (
    "dockerfile",
    "docker-compose",
    ".tf",
    ".tfvars",
    "serverless.yml",
    "serverless.yaml",
    ".github/workflows",
    ".gitlab-ci.yml",
    "k8s",
    "kustomization",
    "helm",
    "values.yaml",
    "appsettings",
    "wrangler",
    "vercel.json",
    "netlify.toml",
)

ENV_FILES = {".env", ".env.local", ".env.production", ".env.development"}

ENCRYPTION_AT_REST = re.compile(
    r"""(?ix)
    (
        storage_encrypted\s*=\s*true |
        encryption_at_rest_options |
        encrypted\s*[:=]\s*true |
        sse[:_-]?algorithm |
        AES256 |
        kms_key_id |
        kms-key-id |
        encryption-config |
        encrypted_disk |
        EnableEncryptionAtRest
    )
    """
)

OBJECT_STORAGE_ENCRYPTION = re.compile(
    r"""(?ix)
    (
        ServerSideEncryptionConfiguration |
        BucketServerSideEncryptionConfiguration |
        bucket_server_side_encryption_configuration |
        default_encryption |
        sse_algorithm
    )
    """
)

BACKUPS_ENCRYPTED = re.compile(
    r"""(?ix)
    (
        backup_retention |
        snapshot_encrypted |
        copy_tags_to_snapshot.*encrypted |
        delete_automated_backups\s*=\s*false
    )
    """
)

TLS_MIN_OK = re.compile(
    r"""(?ix)
    (
        TLSv1\.2 |
        TLSv1\.3 |
        min_tls_version\s*=\s*[\"\']?TLS_?1[._]2 |
        ssl_protocols.*TLSv1\.2
    )
    """
)
TLS_MIN_BAD = re.compile(
    r"""(?ix)
    (
        TLSv1\.0 |
        TLSv1\.1 |
        sslv3 |
        sslv2 |
        min_tls_version\s*=\s*[\"\']?TLS_?1[._]0
    )
    """
)

HSTS = re.compile(
    r"""(?ix)
    Strict-Transport-Security |
    hsts(?:Options)? |
    forceSSL |
    force-ssl-redirect
    """
)

PUBLIC_BUCKET = re.compile(
    r"""(?ix)
    acl\s*[:=]\s*[\"\']?public-read |
    public_access_block_configuration\s*=\s*false |
    block_public_acls\s*=\s*false
    """
)

LOG_RETENTION = re.compile(
    r"""(?ix)
    retention_in_days\s*=\s*(?P<days>\d+) |
    log_retention\s*[:=]\s*(?P<days2>\d+)
    """
)

SECRET_VAL = re.compile(
    r"""(?ix)
    ^\s*
    (?P<key>[A-Z][A-Z0-9_]+(?:KEY|TOKEN|SECRET|PASSWORD|PWD|DSN|URL))
    \s*=\s*
    (?P<val>[^\s#]+)
    """,
    re.MULTILINE,
)


@dataclass
class InfraFacts:
    db_encryption_at_rest: bool = False
    object_storage_encryption: bool = False
    backups_encrypted: bool = False
    tls_min_version_ok: bool = False
    tls_min_version_bad: bool = False
    hsts_enabled: bool = False
    public_bucket_count: int = 0
    log_retention_days_max: int = 0
    env_committed_count: int = 0
    risk_analysis_doc_present: bool = False
    incident_runbook_present: bool = False
    mfa_evidence: bool = False
    log_retention_evidence: bool = False
    samples: dict[str, list[str]] = field(default_factory=dict)

    def add_sample(self, key: str, s: str) -> None:
        self.samples.setdefault(key, [])
        if len(self.samples[key]) < 8 and s not in self.samples[key]:
            self.samples[key].append(s)


def is_infra_file(path: Path) -> bool:
    s = str(path).lower()
    return any(h in s for h in INFRA_FILE_HINTS) or path.name.lower() in {
        "dockerfile", "vercel.json", "netlify.toml"
    }


def is_env_file(path: Path) -> bool:
    return path.name in ENV_FILES or path.name.startswith(".env.")


def is_doc_file(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".rst", ".adoc", ".txt"}


def walk(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue
        yield path


def scan_infra(path: Path, facts: InfraFacts) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    if ENCRYPTION_AT_REST.search(text):
        facts.db_encryption_at_rest = True
        facts.add_sample("db_encryption_at_rest", str(path))
    if OBJECT_STORAGE_ENCRYPTION.search(text):
        facts.object_storage_encryption = True
        facts.add_sample("object_storage_encryption", str(path))
    if BACKUPS_ENCRYPTED.search(text):
        facts.backups_encrypted = True
        facts.add_sample("backups_encrypted", str(path))
    if TLS_MIN_OK.search(text):
        facts.tls_min_version_ok = True
        facts.add_sample("tls_min_version_ok", str(path))
    if TLS_MIN_BAD.search(text):
        facts.tls_min_version_bad = True
        facts.add_sample("tls_min_version_bad", str(path))
    if HSTS.search(text):
        facts.hsts_enabled = True
        facts.add_sample("hsts_enabled", str(path))
    for m in PUBLIC_BUCKET.finditer(text):
        facts.public_bucket_count += 1
        facts.add_sample("public_bucket", f"{path} — {m.group(0)[:100]}")
    for m in LOG_RETENTION.finditer(text):
        days = int(m.group("days") or m.group("days2") or 0)
        if days > facts.log_retention_days_max:
            facts.log_retention_days_max = days


def scan_env(path: Path, facts: InfraFacts) -> None:
    facts.env_committed_count += 1
    facts.add_sample("env_committed", str(path))


def scan_docs(path: Path, facts: InfraFacts) -> None:
    name = path.name.lower()
    hints_risk = ("risk-analysis", "risk_analysis", "risk-assessment", "ra_doc")
    hints_inc = ("incident-response", "incident_response", "runbook", "ir-plan", "ir_plan")
    hints_mfa = ("mfa", "two-factor", "2fa", "auth-policy")
    hints_ret = ("log-retention", "retention-policy", "log_retention")
    s = name + " " + path.stem.lower()
    if any(h in s for h in hints_risk):
        facts.risk_analysis_doc_present = True
        facts.add_sample("risk_analysis_doc", str(path))
    if any(h in s for h in hints_inc):
        facts.incident_runbook_present = True
        facts.add_sample("incident_runbook", str(path))
    if any(h in s for h in hints_mfa):
        facts.mfa_evidence = True
        facts.add_sample("mfa_evidence", str(path))
    if any(h in s for h in hints_ret):
        facts.log_retention_evidence = True
        facts.add_sample("log_retention", str(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.project.resolve()
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 2

    facts = InfraFacts()
    files = 0
    for path in walk(root):
        files += 1
        if is_env_file(path):
            scan_env(path, facts)
            continue
        if is_doc_file(path):
            scan_docs(path, facts)
        if is_infra_file(path) or path.suffix.lower() in {".yml", ".yaml", ".tf", ".tfvars", ".json"}:
            scan_infra(path, facts)

    if facts.log_retention_days_max >= 2190:
        facts.log_retention_evidence = True

    if facts.tls_min_version_ok and not facts.tls_min_version_bad:
        tls_ok = True
    elif facts.tls_min_version_bad:
        tls_ok = False
    else:
        tls_ok = False

    out = {
        "infra": {
            "db_encryption_at_rest": facts.db_encryption_at_rest,
            "object_storage_encryption": facts.object_storage_encryption,
            "backups_encrypted": facts.backups_encrypted,
            "tls_min_version_ok": tls_ok,
            "tls_min_version_bad": facts.tls_min_version_bad,
            "hsts_enabled": facts.hsts_enabled,
            "public_bucket_count": facts.public_bucket_count,
            "log_retention_days_max": facts.log_retention_days_max,
            "env_committed_count": facts.env_committed_count,
            "risk_analysis_doc_present": facts.risk_analysis_doc_present,
            "incident_runbook_present": facts.incident_runbook_present,
            "mfa_evidence": facts.mfa_evidence,
            "log_retention_evidence": facts.log_retention_evidence,
            "samples": facts.samples,
        },
        "infra_files_scanned": files,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"scan_infra: {files} files → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
