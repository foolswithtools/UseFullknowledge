---
id: ga4-data-api-auth-and-traffic-pull-a1b2
title: "GA4 Data API: Authentication and Traffic Data Pull"
type: explainer
summary: "How to authenticate with Google Analytics 4 Data API using service account credentials, pull traffic data by channel/source/medium, and troubleshoot common errors. Covers credential setup, GitHub Secrets integration, and key metrics for lead management analysis."
tags: [ga4, google-analytics, api, authentication, traffic-analysis, lead-management]
created_at: "2026-09-06T22:10:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4-6
updated_at: "2026-09-06T22:10:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only, primary-source-cited]
volatility: fast
sources:
  - https://developers.google.com/analytics/devguides/reporting/data/v1
---

## Summary

GA4 Data API (v1beta) requires a Google Cloud service account with JSON credentials and the GA4 Property ID. You pull traffic data by specifying date ranges, dimensions (channel, source, medium), and metrics (sessions, users, pageviews, conversions). Credentials can be stored as GitHub Secrets for CI/CD pipelines.

## Context

Agents and developers pulling Google Analytics 4 traffic data for lead management analysis — channel attribution, traffic quality assessment, conversion tracking. The main challenge is credential setup: GA4 uses service accounts (not API keys), and the credential format must be handled correctly.

## How it works

### Authentication

GA4 Data API uses Google Cloud service accounts:

1. **Create a service account** in Google Cloud Console
2. **Generate a JSON key** for the service account
3. **Add the service account email** to your GA4 property as a user (Viewer role)
4. **Use the JSON credentials** to authenticate API calls

**Credential format** (JSON):
```json
{
  "type": "service_account",
  "project_id": "your-project",
  "private_key_id": "...",
  "private_key": "<YOUR_PRIVATE_KEY_HERE>",
  "client_email": "sa-name@project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

### GitHub Secrets Integration

Store credentials as GitHub Secrets (never in code):

| Secret | Description |
|--------|-------------|
| `GA4_PROPERTY_ID` | Numeric GA4 property ID (found in GA4 → Admin → Property Settings) |
| `GA4_CLIENT_EMAIL` | Service account email from JSON key |
| `GA4_PRIVATE_KEY` | Private key from JSON key (includes `\n` characters) |

**Important:** When storing the private key as a GitHub Secret, the `\n` characters in the key may need to be converted to actual newlines at runtime:
```python
private_key = private_key.replace('\\n', '\n')
```

### API Endpoint: Run Report

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_info({
    "type": "service_account",
    "private_key": private_key.replace('\\n', '\n'),
    "client_email": client_email,
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": ""
})

client = BetaAnalyticsDataClient(credentials=credentials)

request = RunReportRequest(
    property=f"properties/{property_id}",
    date_ranges=[DateRange(start_date="2026-09-05", end_date="2026-09-05")],
    dimensions=[
        Dimension(name="sessionDefaultChannelGroup"),
        Dimension(name="sessionSource"),
        Dimension(name="sessionMedium"),
    ],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="screenPageViews"),
        Metric(name="conversions"),
        Metric(name="averageSessionDuration"),
    ],
)

response = client.run_report(request)
```

### Key Dimensions for Lead Management

| Dimension | Description | Use Case |
|-----------|-------------|----------|
| `sessionDefaultChannelGroup` | Channel classification (Paid Search, Organic, Social, etc.) | Channel-level attribution |
| `sessionSource` | Traffic source (Google, Facebook, direct) | Source-level attribution |
| `sessionMedium` | Medium (cpc, organic, referral) | Medium-level analysis |
| `eventName` | Specific events fired | Conversion breakdown by event type |
| `pageTitle` | Page title | Content performance |
| `landingPagePlusQueryString` | Landing page URL | Entry point analysis |

### Key Metrics

| Metric | Description |
|--------|-------------|
| `sessions` | Number of sessions |
| `totalUsers` | Unique users |
| `screenPageViews` | Total page views |
| `conversions` | Count of conversion events |
| `averageSessionDuration` | Average session duration (seconds) |

### Understanding "Conversions"

In GA4, conversions are events explicitly marked as conversion events in GA4 property settings. By default, GA4 marks `purchase`, `sign_up`, and `generate_lead` as conversions. You can mark any custom event as a conversion.

To see which events are marked as conversions:
 GA4 → Admin → Events → look for events with "Mark as conversion" toggled ON

To pull conversions broken down by event name, add `Dimension(name="eventName")` to the request.

### Installing Required Libraries

```bash
pip install google-analytics-data google-auth
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| 403 Permission Denied | Service account not added to GA4 property | Add service account email as Viewer in GA4 → Admin → Property Access Management |
| 404 Property Not Found | Wrong property ID format | Use numeric property ID (found in GA4 → Admin → Property Settings), not measurement ID |
| Invalid private key | `\n` not converted to newlines | Use `private_key.replace('\\n', '\n')` |
| No data returned | Date range has no data or property ID is wrong | Verify property ID and date range; check service account has access |

## What this is not

This is not a guide to GA4's Measurement Protocol (for sending custom events to GA4) or GA4's Admin API (for managing properties). This covers only the Data API for pulling report data.

This is also not a guide to Universal Analytics (UA), which is deprecated. GA4 Data API is the replacement for UA's Reporting API.

## References

- GA4 Data API docs: https://developers.google.com/analytics/devguides/reporting/data/v1
- GA4 Data API reference: https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
- Service account setup: https://cloud.google.com/iam/docs/creating-managing-service-accounts
