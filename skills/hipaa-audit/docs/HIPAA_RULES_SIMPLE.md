# HIPAA — Simple Explainer (for engineers + CTOs)

> Plain English. No jargon when avoidable. Read in 10 min, understand 80% of what compliance teams obsess over.

---

## What HIPAA actually is

A US federal law (1996) that protects **health information**. Anyone touching that data — directly or as a vendor — has rules to follow.

**The data it protects = PHI** (Protected Health Information): name + any of 17 other identifiers tied to a health condition, treatment, or payment.

---

## Who it applies to

| Role | Meaning | Example |
|------|---------|---------|
| **Covered Entity (CE)** | Provider, insurer, clearinghouse | Hospital, clinic, BlueCross |
| **Business Associate (BA)** | Vendor that handles PHI on behalf of a CE | Your SaaS, your AWS, your Stripe |
| **Subcontractor** | A BA's vendor that also touches PHI | Your Sentry, your Datadog |

**Rule of thumb:** if you're building software that any clinic, hospital, or insurer will use to store/process patient data — you are a BA. You need a **BAA** (Business Associate Agreement) with them, and with every vendor downstream.

**No BAA = automatic violation if PHI flows.**

---

## The 3 rules to remember

### 1. Privacy Rule — *Who can see PHI*

- **Minimum necessary** — only show what's needed for the task
- Patients have rights: see their data, request fixes, get a list of who you shared it with
- Need written authorization for anything outside Treatment / Payment / Operations (TPO)

### 2. Security Rule — *How to protect electronic PHI (ePHI)*

Splits into three buckets of safeguards:

| Bucket | What it covers |
|--------|----------------|
| **Administrative** | People + policies — training, risk analysis, access mgmt, incident response, BAAs |
| **Physical** | Buildings + devices — facility access, workstation rules, device disposal |
| **Technical** | Software — access control, audit logs, integrity, transmission security (encryption) |

Each control is marked **Required** (must do) or **Addressable** (must do *unless* you document why a different control is equivalent). "Addressable" ≠ optional.

### 3. Breach Notification Rule — *What to do when you leak*

- Affected < 500 → notify individuals in 60 days, report to HHS yearly
- Affected ≥ 500 → notify individuals + HHS + media in 60 days
- Burden is on **you** to prove no harm occurred. Default = breach.

---

## What PHI looks like (the 18 identifiers)

Any of these + health info = PHI:

1. Names
2. Geographic info smaller than state (street, city, ZIP)
3. Dates (DOB, admission, discharge, death — except year)
4. Phone numbers
5. Fax numbers
6. Email addresses
7. SSN
8. Medical record numbers (MRN)
9. Health plan / insurance numbers
10. Account numbers
11. License / certificate numbers
12. Vehicle identifiers (plates, VIN)
13. Device serial numbers
14. URLs identifying individuals
15. IP addresses
16. Biometric IDs (fingerprint, voice, retina)
17. Full-face photos
18. Any other unique identifying code

**Safe Harbor** = strip all 18 → no longer PHI → less regulation.

---

## What to actually build (engineer's view)

### Encryption
- **At rest:** AES-256. Every database, backup, object store, log volume.
- **In transit:** TLS 1.2+ only. HSTS on. Disable HTTP entirely.

### Access control
- Unique user ID per person (no shared admins)
- MFA on anything privileged
- Role-based access control (RBAC), least privilege
- Auto-logoff (15 min idle is common)

### Audit logs
- Every PHI access (read AND write) logged
- Immutable storage (write-once or append-only)
- Retain ≥ 6 years
- Include: who, what record, when, from where, action

### No PHI in dumb places
- ❌ Logs — strip before write
- ❌ URLs — `?ssn=...` is a nightmare
- ❌ Email/SMS plaintext — use portal link
- ❌ Analytics pixels on patient pages (Google Analytics, Meta Pixel — HHS flagged these)
- ❌ Error trackers (Sentry, Datadog) without scrubbing
- ❌ Screenshots / mobile cache without lock

### Dev/staging
- Use synthetic or de-identified data only
- No real patient data in non-prod

### Vendor BAA chain
Every third party touching PHI needs a signed BAA:
- AWS (yes, available)
- GCP (yes, available)
- Azure (yes, available)
- Stripe (yes, available — sign their BAA)
- Twilio (yes — sign theirs)
- SendGrid (yes)
- Sentry (yes, Enterprise plan only)
- Datadog (yes, Enterprise plan only)
- Vercel (yes, Enterprise plan only)
- Firebase (yes, but specific services only)
- Google Analytics (**NO BAA** — replace it)
- Meta Pixel (**NO BAA** — replace it)
- Mixpanel (**NO BAA** for standard product)

### Incident response
- Written plan, tested via tabletop ≥ yearly
- 60-day notification clock starts at discovery
- Forensics ready: who, what, when, scope

---

## Penalties (so you take it seriously)

| Tier | Per violation | Annual cap |
|------|---------------|------------|
| 1 — No knowledge | $137–$68k | $2M |
| 2 — Reasonable cause | $1.4k–$68k | $2M |
| 3 — Wilful, corrected | $14k–$68k | $2M |
| 4 — Wilful, uncorrected | $68k+ | $2M |

Plus criminal penalties up to 10yr prison. State AGs can pile on. Plus reputational damage. Plus class-action lawsuits.

---

## What HIPAA does NOT cover

- Health apps you build for consumers (not tied to a covered entity) — covered by FTC instead
- Fitness trackers, generic wellness apps
- De-identified data (after Safe Harbor)
- Employer health records (employment use)
- Data in non-US jurisdictions (those have GDPR / PIPEDA / etc.)

---

## CTO-level priorities (Pareto 80/20)

If you only do 5 things, do these:

1. **Sign BAAs with every vendor.** Inventory them. Audit annually.
2. **Encrypt everything.** At rest + in transit. No exceptions.
3. **Strip PHI from logs and URLs.** Scrubber library at the boundary.
4. **Audit log every PHI read/write.** Immutable. 6-year retention.
5. **Risk analysis doc.** Annual. NIST 800-30 format. This is the #1 thing OCR asks for in an investigation.

Then add: MFA, RBAC, incident response plan, dev data de-id, breach notification runbook.

---

## How auditors think

OCR (the HHS office that enforces) audits in two modes:

- **Random / scheduled audit** — they request the risk analysis, BAA list, training logs, policies. Pure paperwork.
- **Breach-triggered investigation** — they reverse-engineer your security from the incident.

Both want **evidence**, not assertions. Date-stamped, signed, retained.

This skill helps you generate that evidence on the technical side.
