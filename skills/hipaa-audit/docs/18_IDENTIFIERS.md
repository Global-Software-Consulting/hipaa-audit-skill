# Safe Harbor — 18 Identifiers (45 CFR § 164.514(b)(2))

Strip ALL 18 and you have de-identified data. Anything tied to health info + any one of these = PHI.

| # | Identifier | Pattern hints for detection |
|---|------------|----------------------------|
| 1 | Names | Patient, family, provider names |
| 2 | Geographic subdivisions < state | Street, city, county, ZIP (first 3 digits OK if pop > 20k) |
| 3 | Dates (except year) | DOB, admission, discharge, death, service. Year-only OK. >89 → "90+" |
| 4 | Telephone numbers | `\d{3}[-.\s]?\d{3}[-.\s]?\d{4}` |
| 5 | Fax numbers | Same as phone |
| 6 | Email addresses | `[\w.+-]+@[\w-]+\.[\w.-]+` |
| 7 | Social Security numbers | `\d{3}-\d{2}-\d{4}` or 9-digit blocks |
| 8 | Medical record numbers (MRN) | Hospital/clinic IDs |
| 9 | Health plan beneficiary numbers | Insurance member ID, policy # |
| 10 | Account numbers | Billing, financial |
| 11 | Certificate / license numbers | Driver's license, professional license |
| 12 | Vehicle identifiers | License plate, VIN |
| 13 | Device identifiers | Serial numbers (pacemaker, implant) |
| 14 | Web URLs | Personal sites identifying individuals |
| 15 | IP addresses | IPv4/IPv6 |
| 16 | Biometric identifiers | Fingerprints, voice, retinal scan |
| 17 | Full-face photographs | Black bars over eyes ≠ sufficient |
| 18 | Any other unique code | Rare disease + age + region combos can re-identify |

## Two de-identification methods

### Safe Harbor (default, easier)
- Strip all 18
- Confirm no actual knowledge that remaining info could re-identify
- Done

### Expert Determination
- Qualified statistician proves "very small" re-identification risk
- Allows retention of some identifiers (e.g., dates for time-series)
- Requires documented methodology

## Limited Data Set

Strips 16 of 18, may retain:
- Dates (admission, discharge, service, DOB, death)
- Geographic info (city, state, ZIP)

Requires **Data Use Agreement (DUA)**. Use for research, public health, healthcare operations only. Recipient agrees not to re-identify.

## Source

- 45 CFR § 164.514(b)(2) — Safe Harbor
- 45 CFR § 164.514(b)(1) — Expert Determination
- 45 CFR § 164.514(e) — Limited Data Set
- HHS guidance: https://www.hhs.gov/hipaa/for-professionals/privacy/special-topics/de-identification/index.html
