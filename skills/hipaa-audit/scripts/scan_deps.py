#!/usr/bin/env python3
"""
Scan dependency manifests, map to BAA status table.

Reads:
  - package.json (npm/yarn/pnpm)
  - requirements.txt, Pipfile, pyproject.toml (python)
  - go.mod (go)
  - Gemfile (ruby)
  - pom.xml (maven)
  - composer.json (php)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# baa: "signable" | "enterprise_required" | "blocked"
VENDOR_MAP = [
    # NO BAA — must replace
    ("google-analytics", ["react-ga", "react-ga4", "@analytics/google-analytics", "gtag"], "blocked"),
    ("meta-pixel", ["react-facebook-pixel", "facebook-pixel"], "blocked"),
    ("tiktok-pixel", ["tiktok-pixel"], "blocked"),
    ("linkedin-insight", ["linkedin-insight"], "blocked"),
    ("mixpanel-standard", ["mixpanel", "mixpanel-browser"], "blocked"),
    ("mailchimp", ["@mailchimp/", "mailchimp-marketing"], "blocked"),
    ("postmark", ["postmark"], "blocked"),
    ("crashlytics", ["@react-native-firebase/crashlytics", "firebase/crashlytics"], "blocked"),
    ("firebase-analytics", ["@react-native-firebase/analytics", "firebase/analytics"], "blocked"),

    # Enterprise BAA required — must verify tier
    ("sentry", ["@sentry/", "sentry-sdk", "raven"], "enterprise_required"),
    ("datadog", ["dd-trace", "datadog-api-client", "@datadog/"], "enterprise_required"),
    ("new-relic", ["newrelic", "new-relic"], "enterprise_required"),
    ("vercel-host", ["@vercel/", "vercel"], "enterprise_required"),
    ("logrocket", ["logrocket"], "enterprise_required"),
    ("fullstory", ["@fullstory/"], "enterprise_required"),
    ("heap", ["heap-analytics"], "enterprise_required"),
    ("cloudflare", ["cloudflare"], "enterprise_required"),

    # BAA signable (standard)
    ("aws", ["aws-sdk", "@aws-sdk/", "boto3", "boto"], "signable"),
    ("gcp", ["@google-cloud/", "google-cloud-"], "signable"),
    ("azure", ["@azure/", "azure-"], "signable"),
    ("stripe", ["stripe", "@stripe/"], "signable"),
    ("twilio", ["twilio", "@twilio/"], "signable"),
    ("sendgrid", ["@sendgrid/", "sendgrid"], "signable"),
    ("mailgun", ["mailgun-js", "mailgun.js"], "signable"),
    ("auth0", ["auth0", "@auth0/"], "signable"),
    ("okta", ["@okta/", "okta-"], "signable"),
    ("clerk", ["@clerk/"], "signable"),
    ("supabase", ["@supabase/"], "signable"),
    ("mongodb-atlas", ["mongodb", "mongoose"], "signable"),
    ("snowflake", ["snowflake-sdk"], "signable"),
    ("heroku-shield", ["heroku-cli"], "signable"),
    ("openai", ["openai"], "signable"),
    ("anthropic", ["@anthropic-ai/", "anthropic"], "signable"),
]

AUTH_FRAMEWORKS = {
    "next-auth", "@auth/core", "passport", "passport-jwt", "passport-local",
    "@clerk/", "@auth0/", "@okta/", "express-jwt", "django-allauth",
    "devise", "spring-boot-starter-security", "@nestjs/passport",
}

VALIDATION_LIBS = {
    "zod", "yup", "joi", "ajv", "class-validator", "pydantic", "marshmallow",
    "express-validator", "fastify-type-provider", "valibot",
}


def parse_package_json(p: Path) -> set[str]:
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return set()
    deps: set[str] = set()
    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps.update((data.get(k) or {}).keys())
    return deps


def parse_requirements_txt(p: Path) -> set[str]:
    out: set[str] = set()
    try:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
            if m:
                out.add(m.group(1).lower())
    except OSError:
        pass
    return out


def parse_pipfile(p: Path) -> set[str]:
    out: set[str] = set()
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    in_pkg = False
    for line in text.splitlines():
        s = line.strip()
        if s in ("[packages]", "[dev-packages]"):
            in_pkg = True
            continue
        if s.startswith("[") and s != "[packages]" and s != "[dev-packages]":
            in_pkg = False
        if in_pkg and "=" in s:
            out.add(s.split("=", 1)[0].strip().strip('"').lower())
    return out


def parse_go_mod(p: Path) -> set[str]:
    out: set[str] = set()
    try:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"\s*([\w\.\-/]+)\s+v", line)
            if m:
                out.add(m.group(1).lower())
    except OSError:
        pass
    return out


def parse_gemfile(p: Path) -> set[str]:
    out: set[str] = set()
    try:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"\s*gem\s+['\"]([^'\"]+)['\"]", line)
            if m:
                out.add(m.group(1).lower())
    except OSError:
        pass
    return out


def parse_pom_xml(p: Path) -> set[str]:
    out: set[str] = set()
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return out
    for m in re.finditer(r"<artifactId>([^<]+)</artifactId>", text):
        out.add(m.group(1).lower())
    return out


def parse_composer_json(p: Path) -> set[str]:
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[str] = set()
    for k in ("require", "require-dev"):
        out.update((data.get(k) or {}).keys())
    return out


def gather_deps(root: Path) -> set[str]:
    deps: set[str] = set()
    for p in root.rglob("package.json"):
        if "node_modules" in p.parts:
            continue
        deps.update(parse_package_json(p))
    for p in root.rglob("requirements*.txt"):
        deps.update(parse_requirements_txt(p))
    for p in root.rglob("Pipfile"):
        deps.update(parse_pipfile(p))
    for p in root.rglob("go.mod"):
        deps.update(parse_go_mod(p))
    for p in root.rglob("Gemfile"):
        deps.update(parse_gemfile(p))
    for p in root.rglob("pom.xml"):
        deps.update(parse_pom_xml(p))
    for p in root.rglob("composer.json"):
        if "vendor" in p.parts:
            continue
        deps.update(parse_composer_json(p))
    return {d.lower() for d in deps if d}


def classify(deps: set[str]):
    matches: list[dict] = []
    seen: set[str] = set()
    for vendor, pats, baa in VENDOR_MAP:
        for d in deps:
            if vendor in seen:
                break
            for pat in pats:
                if pat.lower() in d:
                    matches.append({"vendor": vendor, "package": d, "baa": baa})
                    seen.add(vendor)
                    break
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.project.resolve()
    deps = gather_deps(root)
    matches = classify(deps)

    blocked = [m for m in matches if m["baa"] == "blocked"]
    enterprise = [m for m in matches if m["baa"] == "enterprise_required"]
    signable = [m for m in matches if m["baa"] == "signable"]

    auth_present = any(any(a.lower() in d for a in AUTH_FRAMEWORKS) for d in deps)
    validation_present = any(v in deps for v in VALIDATION_LIBS)

    out = {
        "deps": {
            "total_deps_scanned": len(deps),
            "baa_blocked_count": len(blocked),
            "baa_enterprise_required_count": len(enterprise),
            "baa_signable_count": len(signable),
            "auth_framework_present": auth_present,
            "validation_lib_present": validation_present,
            "matches": matches,
        }
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"scan_deps: {len(deps)} deps, {len(matches)} vendor matches → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
