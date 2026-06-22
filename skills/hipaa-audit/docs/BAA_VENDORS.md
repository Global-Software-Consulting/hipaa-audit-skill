# Common Vendor BAA Status

> Heuristic map. **Always confirm** on the vendor's current HIPAA page. Status changes; this doc updated 2026-06.

## Will sign BAA (PHI safe with config)

| Vendor | Notes |
|--------|-------|
| AWS | BAA via AWS Artifact. HIPAA-eligible service list applies. |
| Google Cloud | BAA via Workspace admin or GCP. Eligible services only. |
| Microsoft Azure | BAA in OST. Most services covered. |
| Stripe | Sign Stripe's BAA. Limits on data fields you can pass. |
| Twilio | BAA on Enterprise. Limited to SMS/voice content. |
| SendGrid | BAA on Enterprise plan. |
| Mailgun | BAA on HIPAA plan only. |
| Postmark | No BAA. (Often misremembered.) |
| Sentry | BAA on Enterprise / Business plan with HIPAA add-on. |
| Datadog | BAA on Enterprise. PHI scrubbing required. |
| New Relic | BAA on Enterprise plan. |
| LogRocket | BAA available; scrubbing config required. |
| FullStory | BAA available; element masking required. |
| Vercel | BAA on Enterprise. |
| Netlify | BAA on Enterprise (Reserved Compute). |
| Cloudflare | BAA on Enterprise. |
| MongoDB Atlas | BAA on M10+ dedicated clusters. |
| Snowflake | BAA via Business Critical edition. |
| Heroku | BAA via Shield Private Spaces. |
| Salesforce | BAA via Health Cloud / specific editions. |
| HubSpot | BAA on Enterprise (recently added). Verify scope. |
| Intercom | BAA available; specific config. |
| Auth0 | BAA on Enterprise. |
| Okta | BAA available. |
| Clerk | BAA on Enterprise. |
| Supabase | BAA on Team/Enterprise. |
| Firebase | BAA covers Auth, Firestore, RTDB, Cloud Storage, Cloud Functions. NOT Crashlytics, Analytics, Performance, Remote Config. |
| OpenAI | BAA via Enterprise / zero-retention API. |
| Anthropic | BAA available via enterprise contract. |

## Will NOT sign BAA (replace if PHI flows)

| Vendor | Replacement |
|--------|-------------|
| Google Analytics (GA4) | Remove from patient-facing pages. HHS flagged 2022. |
| Meta Pixel | Remove. HHS flagged 2022. Multiple hospitals settled lawsuits. |
| TikTok Pixel | Remove. |
| LinkedIn Insight Tag | Remove. |
| Mixpanel | No standard BAA; check enterprise. Often replaced w/ Heap (Enterprise) or PostHog (self-host). |
| Heap Analytics | BAA on Enterprise only; standard tier = no. |
| Crashlytics (Firebase) | No BAA. Strip from healthcare apps. |
| Firebase Analytics | No BAA. Use proxy or remove. |
| Postmark | Use Mailgun HIPAA or Paubox. |
| ConvertKit | Use HIPAA-compliant ESP. |
| Mailchimp | No BAA. Use Mailgun HIPAA. |
| Slack (standard) | No BAA. Use Slack Enterprise Grid with EKM, or Mattermost. |
| Discord | No BAA. |
| Notion | No BAA on standard plans. Enterprise has limited BAA scope. |
| Airtable | No BAA on standard. Enterprise scale plan only. |
| Zapier | No BAA on most plans. |

## Detection patterns (used by `scan_deps.py`)

```yaml
# package.json / requirements.txt match → flag for BAA check
- name: google-analytics
  patterns: ["ga", "gtag", "react-ga", "react-ga4", "@analytics/google-analytics"]
  baa: false
  severity: must

- name: meta-pixel
  patterns: ["react-facebook-pixel", "fbq", "facebook-pixel"]
  baa: false
  severity: must

- name: sentry
  patterns: ["@sentry/", "sentry-sdk"]
  baa: enterprise_required
  severity: should

- name: stripe
  patterns: ["stripe", "@stripe/"]
  baa: signable
  severity: should
```

## References

- HHS guidance on tracking technologies: https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html
- AWS HIPAA-eligible services: https://aws.amazon.com/compliance/hipaa-eligible-services-reference/
- GCP HIPAA-covered services: https://cloud.google.com/security/compliance/hipaa
