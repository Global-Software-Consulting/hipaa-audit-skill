# Off-Code Compliance Interview

> Claude reads this file after the auto-scan completes, then asks the user each section's questions ONE AT A TIME. Answers are written to `interview.json` in the audit output dir. `merge_interview.py` then combines scan + interview into the final report.

Each question has:
- `id` — stable key for the answer file
- `category` — buckets findings
- `severity` — must / should / nice
- `prompt` — verbatim wording Claude asks
- `accept` — accepted shapes: `yes_no`, `yes_no_partial`, `text`, `date`, `number`, `enum:a|b|c`, `multi:a,b,c`
- `evidence_prompt` — follow-up asking for proof location/doc link

Claude rules when running this interview:
1. Ask in batches of **3–5 questions per turn**. Never dump all at once.
2. Start with **MUST severity** questions first. Hold SHOULD/NICE for the end.
3. For each "no" or "partial" answer, ask the `evidence_prompt`.
4. If the user says "skip" or "don't know" → record `unknown` with note.
5. After each batch, summarize what was captured. Save to `interview.json` after each batch (resumable).
6. When all MUST done, offer to stop or continue with SHOULD/NICE.

---

## Section 1 — Business Associate Agreements (MUST)

```yaml
- id: baa.with_covered_entity
  category: dep-baa
  severity: must
  prompt: "Do you have a signed Business Associate Agreement (BAA) with every covered entity (hospital, clinic, insurer) that sends PHI to your system?"
  accept: yes_no_partial
  evidence_prompt: "Where are these BAAs stored? Link to repository / drive / contract management tool."

- id: baa.with_subprocessors
  category: dep-baa
  severity: must
  prompt: "For every vendor your app sends PHI to (cloud, email, error tracker, analytics, CDN, etc.), have you signed their BAA?"
  accept: yes_no_partial
  evidence_prompt: "Which vendors are missing a BAA? Paste vendor names."

- id: baa.review_cadence
  category: dep-baa
  severity: should
  prompt: "How often do you review the BAA vendor list for additions/changes?"
  accept: enum:never|annually|quarterly|monthly
  evidence_prompt: "Where is the BAA inventory tracked?"
```

---

## Section 2 — Risk Analysis & Risk Management (MUST)

```yaml
- id: risk.analysis_doc
  category: breach-readiness
  severity: must
  prompt: "Is there a written HIPAA risk analysis document covering threats, vulnerabilities, likelihood, impact, and mitigations (NIST 800-30 format)?"
  accept: yes_no
  evidence_prompt: "Path or URL to the risk analysis document. Date of last review."

- id: risk.review_cadence
  category: breach-readiness
  severity: must
  prompt: "When was the risk analysis last reviewed or updated?"
  accept: date
  evidence_prompt: "Show the review log / changelog."

- id: risk.mitigation_plan
  category: breach-readiness
  severity: should
  prompt: "Is there a risk management plan tracking each identified risk to a remediation owner and deadline?"
  accept: yes_no_partial
  evidence_prompt: "Where is this tracked (ticket system, doc, spreadsheet)?"
```

---

## Section 3 — Workforce & Policies (MUST)

```yaml
- id: workforce.training_log
  category: access-control
  severity: must
  prompt: "Does every workforce member with PHI access complete annual HIPAA training, with a signed acknowledgment on file?"
  accept: yes_no_partial
  evidence_prompt: "Training platform + completion log location."

- id: workforce.sanction_policy
  category: access-control
  severity: must
  prompt: "Is there a written sanction policy for workforce members who violate HIPAA policies?"
  accept: yes_no
  evidence_prompt: "Path to sanction policy document."

- id: workforce.privacy_officer
  category: access-control
  severity: must
  prompt: "Is there a designated Privacy Officer (in writing)?"
  accept: yes_no
  evidence_prompt: "Name + designation date."

- id: workforce.security_officer
  category: access-control
  severity: must
  prompt: "Is there a designated Security Officer (in writing)?"
  accept: yes_no
  evidence_prompt: "Name + designation date."

- id: workforce.termination_procedure
  category: access-control
  severity: must
  prompt: "When a workforce member leaves, is there a documented procedure to revoke access to all PHI systems within 24 hours?"
  accept: yes_no_partial
  evidence_prompt: "Path to offboarding checklist + most recent termination evidence."
```

---

## Section 4 — Access Reviews (SHOULD)

```yaml
- id: access.review_cadence
  category: access-control
  severity: should
  prompt: "How often is user access to PHI systems reviewed (manager certifies each user still needs each permission)?"
  accept: enum:never|annually|quarterly|monthly
  evidence_prompt: "Where is the access review log kept?"

- id: access.mfa_enforced
  category: access-control
  severity: must
  prompt: "Is MFA enforced for ALL workforce accounts touching PHI (not just admins)?"
  accept: yes_no_partial
  evidence_prompt: "Identity provider + screenshot of MFA enforcement policy."

- id: access.shared_accounts
  category: access-control
  severity: must
  prompt: "Are there any shared accounts (multiple humans using one login) anywhere in the PHI flow?"
  accept: yes_no
  evidence_prompt: "List shared accounts and remediation plan."
```

---

## Section 5 — Audit Logs (MUST)

```yaml
- id: audit.phi_access_logged
  category: audit-logging
  severity: must
  prompt: "Is every PHI READ (not just write) logged with user identity, record id, timestamp, source IP?"
  accept: yes_no_partial
  evidence_prompt: "Sample log line + log destination."

- id: audit.immutable_storage
  category: audit-logging
  severity: must
  prompt: "Are audit logs stored in append-only / immutable storage (cannot be edited or deleted by app users)?"
  accept: yes_no
  evidence_prompt: "Storage location + WORM/immutability config."

- id: audit.retention_6yr
  category: audit-logging
  severity: must
  prompt: "Are audit logs retained for at least 6 years?"
  accept: yes_no
  evidence_prompt: "Retention policy doc + storage lifecycle config."

- id: audit.review_cadence
  category: audit-logging
  severity: should
  prompt: "How often does someone actually review the audit logs (or alerts on anomalies)?"
  accept: enum:never|on_incident|weekly|daily|realtime_alerts
  evidence_prompt: "Tool / runbook used for log review."
```

---

## Section 6 — Encryption (MUST)

```yaml
- id: encrypt.runtime_verified
  category: encryption-at-rest
  severity: must
  prompt: "Have you verified at the cloud-console level (not just IaC) that production databases + object stores show encryption enabled?"
  accept: yes_no
  evidence_prompt: "Screenshot or cloud audit report."

- id: encrypt.backup_restore_tested
  category: encryption-at-rest
  severity: should
  prompt: "Have you actually tested restoring an encrypted backup in the last 12 months?"
  accept: yes_no
  evidence_prompt: "DR test date + result."

- id: encrypt.key_management
  category: encryption-at-rest
  severity: must
  prompt: "Are encryption keys managed in KMS / HSM with rotation policy, not stored in app config?"
  accept: yes_no_partial
  evidence_prompt: "KMS used + rotation schedule."

- id: encrypt.tls_external_verified
  category: encryption-in-transit
  severity: must
  prompt: "Have you scanned the public-facing endpoints with SSL Labs / testssl.sh and confirmed grade A and no TLS 1.0/1.1?"
  accept: yes_no
  evidence_prompt: "Most recent SSL Labs report URL or grade."
```

---

## Section 7 — Incident Response (MUST)

```yaml
- id: incident.runbook
  category: breach-readiness
  severity: must
  prompt: "Is there a written incident response runbook covering detection, containment, notification (60-day clock), forensics, postmortem?"
  accept: yes_no
  evidence_prompt: "Runbook path + last review date."

- id: incident.tabletop_test
  category: breach-readiness
  severity: should
  prompt: "When was the last tabletop test of the incident response plan?"
  accept: date
  evidence_prompt: "Tabletop report path."

- id: incident.breach_log
  category: breach-readiness
  severity: must
  prompt: "Is there a log of all incidents (even non-reportable) with response actions taken?"
  accept: yes_no
  evidence_prompt: "Incident log location."

- id: incident.notification_template
  category: breach-readiness
  severity: should
  prompt: "Is there a pre-approved breach notification template (for affected individuals + HHS + media if ≥500)?"
  accept: yes_no
  evidence_prompt: "Template path."
```

---

## Section 8 — Physical Safeguards (MUST)

```yaml
- id: physical.facility_policy
  category: breach-readiness
  severity: must
  prompt: "Is there a written facility access policy for any office/location where workforce handles PHI (even WFH workstation policy counts)?"
  accept: yes_no
  evidence_prompt: "Policy doc path."

- id: physical.device_disposal
  category: breach-readiness
  severity: must
  prompt: "Is there a documented procedure for secure disposal / sanitization of devices that have stored PHI (NIST 800-88)?"
  accept: yes_no
  evidence_prompt: "Disposal procedure + last sanitization log."

- id: physical.workstation_security
  category: breach-readiness
  severity: should
  prompt: "Are workforce workstations required to have disk encryption, auto-lock, antivirus, MDM enrollment?"
  accept: yes_no_partial
  evidence_prompt: "MDM tool + enrollment compliance %."
```

---

## Section 9 — Disaster Recovery & Contingency (MUST)

```yaml
- id: dr.plan_document
  category: breach-readiness
  severity: must
  prompt: "Is there a written disaster recovery / contingency plan with documented RTO and RPO targets?"
  accept: yes_no
  evidence_prompt: "DR plan path + RTO/RPO values."

- id: dr.last_test
  category: breach-readiness
  severity: should
  prompt: "When was the last DR test (actual failover or game-day exercise)?"
  accept: date
  evidence_prompt: "DR test report."

- id: dr.backup_offsite
  category: encryption-at-rest
  severity: must
  prompt: "Are backups stored in a geographically separate location from production?"
  accept: yes_no
  evidence_prompt: "Backup region(s) + storage."
```

---

## Section 10 — De-identification & Dev Data (MUST)

```yaml
- id: deid.prod_only_phi
  category: de-identification
  severity: must
  prompt: "Is real PHI used ONLY in production? (no real PHI in staging, dev, demo, sandbox, test fixtures)"
  accept: yes_no
  evidence_prompt: "How is dev/staging data sourced (synthetic generator, anonymization pipeline)?"

- id: deid.method_used
  category: de-identification
  severity: should
  prompt: "When you de-identify data, which method do you use?"
  accept: enum:safe_harbor|expert_determination|limited_data_set|none
  evidence_prompt: "Methodology documentation."

- id: deid.reidentification_test
  category: de-identification
  severity: nice
  prompt: "Has anyone attempted a re-identification test on your de-identified datasets?"
  accept: yes_no
  evidence_prompt: "Test results + statistician credentials."
```

---

## Section 11 — Patient Rights (Privacy Rule — MUST if patient-facing)

```yaml
- id: privacy.npp_published
  category: breach-readiness
  severity: must
  prompt: "Is a Notice of Privacy Practices (NPP) published and accessible to patients?"
  accept: yes_no
  evidence_prompt: "URL to NPP."

- id: privacy.access_request_flow
  category: breach-readiness
  severity: must
  prompt: "Is there a documented process for patients to request a copy of their PHI within 30 days?"
  accept: yes_no
  evidence_prompt: "Process doc + average fulfillment time."

- id: privacy.amendment_flow
  category: breach-readiness
  severity: should
  prompt: "Is there a process for patients to request corrections / amendments to their PHI?"
  accept: yes_no
  evidence_prompt: "Process doc."

- id: privacy.accounting_of_disclosures
  category: breach-readiness
  severity: should
  prompt: "Can you produce an accounting of disclosures (every non-TPO disclosure of a patient's PHI) on request?"
  accept: yes_no
  evidence_prompt: "How is this tracked?"

- id: privacy.minimum_necessary
  category: access-control
  severity: must
  prompt: "Is access to PHI restricted to minimum necessary per role (not broad full-database read)?"
  accept: yes_no_partial
  evidence_prompt: "RBAC model overview."
```

---

## Section 12 — Mobile-Specific (if applicable)

```yaml
- id: mobile.cert_pinning
  category: encryption-in-transit
  severity: should
  prompt: "Does the mobile app use certificate pinning for API calls?"
  accept: yes_no_partial
  evidence_prompt: "Pinning library + pinned domains."

- id: mobile.biometric_lock
  category: access-control
  severity: should
  prompt: "Is biometric / passcode lock required to open the app when it contains PHI?"
  accept: yes_no
  evidence_prompt: "Implementation library."

- id: mobile.screenshot_disabled
  category: phi-in-logs
  severity: should
  prompt: "Are screenshots / screen-recording disabled on PHI screens (FLAG_SECURE on Android, screen capture protection on iOS)?"
  accept: yes_no_partial
  evidence_prompt: "Which screens protected."

- id: mobile.background_blur
  category: phi-in-logs
  severity: nice
  prompt: "Does the app blur or hide PHI on the app-switcher / background view?"
  accept: yes_no
  evidence_prompt: "Implementation method."

- id: mobile.no_phi_push
  category: phi-in-logs
  severity: must
  prompt: "Do push notifications avoid PHI in the visible body (no patient name, no diagnosis)?"
  accept: yes_no
  evidence_prompt: "Push payload sample."

- id: mobile.keychain_tokens
  category: secrets-mgmt
  severity: must
  prompt: "Are auth tokens stored in Keychain (iOS) / Keystore (Android), NOT AsyncStorage / SharedPreferences / plain files?"
  accept: yes_no
  evidence_prompt: "Storage implementation."
```

---

## Output schema (`interview.json`)

```json
{
  "completed_at": "2026-06-22T15:00:00Z",
  "sections_completed": ["baa", "risk", "workforce"],
  "answers": {
    "baa.with_covered_entity": {
      "answer": "yes",
      "evidence": "Notion/Compliance/BAA-Inventory.md",
      "note": ""
    },
    "risk.analysis_doc": {
      "answer": "no",
      "evidence": "",
      "note": "scheduled for Q3 2026"
    }
  }
}
```
