---
id: ga4-data-api-auth-and-traffic-pull-a1b2
title: "GA4 Data API: Authentication and Traffic Data Pull"
type: explainer
summary: "How to authenticate with the Google Analytics 4 Data API (v1beta) using a service account, pull traffic data by channel, source and medium, and troubleshoot common errors. Covers enabling the API, granting the service account Viewer access to the property, storing credentials as GitHub Secrets, and the metrics that matter for lead analysis, including keyEvents, which replaced the deprecated conversions metric in May 2024."
tags: [ga4, google-analytics, api, authentication, traffic-analysis, lead-management]
created_at: "2026-09-06T22:10:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4-6
updated_at: "2026-10-05T00:09:45+00:00"
updated_by_kind: agent
updated_by: claude-code
review_status: unreviewed
confidence_basis: [primary-source-cited, model-recall-only]
volatility: fast
sources:
  - https://developers.google.com/analytics/devguides/reporting/data/v1
  - https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart
  - https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
  - https://developers.google.com/analytics/devguides/reporting/data/v1/changelog
  - https://developers.google.com/analytics/devguides/reporting/data/v1/property-id
  - https://developers.google.com/analytics/devguides/reporting/data/v1/errors
  - https://support.google.com/analytics/answer/9305587
  - https://support.google.com/analytics/answer/12844695
---

> **Correction notice (2026-10-04).** Audited against Google's documentation and corrected. The earlier
> version used the `conversions` metric, deprecated in May 2024 and replaced by `keyEvents`; listed
> `purchase`, `sign_up` and `generate_lead` as default conversions (Google's documented defaults are
> `first_open` and `purchase`); gave the old "Mark as conversion" UI path; omitted the step of enabling
> the Data API in the Google Cloud project; and listed a "404 Property Not Found" error that Google does
> not document. It also cited one overview page for claims that page does not cover; each claim now
> cites the page that supports it. Everything else checked out.

## Summary

The GA4 Data API (v1beta) is called with a Google Cloud service account that has Viewer access to the
GA4 property. You request a date range, dimensions (channel, source, medium) and metrics (sessions,
users, page views, key events). Credentials can be stored as GitHub Secrets for CI pipelines.

## Context

Agents and developers pulling Google Analytics 4 traffic data for lead analysis: channel attribution,
traffic quality and key-event tracking. The usual stumbling block is credential setup: the Data API is
called with a service account, and the private key has to survive being stored as a secret.

## How it works

### Authentication

1. **Enable the Google Analytics Data API** (`analyticsdata.googleapis.com`) in your Google Cloud project
   ([quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart)).
2. **Create a service account** in that project
   ([Google Cloud](https://cloud.google.com/iam/docs/service-accounts-create)) and **generate a JSON key**.
3. **Add the service account's email to the GA4 property** under Admin → Property access management,
   with the Viewer role. Viewers can see report data through the user interface or the APIs
   ([GA4 help](https://support.google.com/analytics/answer/9305587)).
4. **Authenticate with the JSON credentials.** The client library's default OAuth scopes cover the Data
   API, so you do not need to set scopes yourself.

**Credential format** (JSON key file):
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

### GitHub Secrets integration

This part is general practice rather than Google documentation. Store credentials as secrets, never in
code:

| Secret | Description |
|--------|-------------|
| `GA4_PROPERTY_ID` | Numeric GA4 property ID, shown in Admin → Property Settings ([how to find it](https://developers.google.com/analytics/devguides/reporting/data/v1/property-id)); not the `G-` measurement ID |
| `GA4_CLIENT_EMAIL` | Service account email from the JSON key |
| `GA4_PRIVATE_KEY` | Private key from the JSON key |

A private key pasted into a secret often arrives with literal `\n` sequences instead of line breaks.
Convert them once at runtime, as in the sample below.

### Run a report

```python
import os

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account

property_id = os.environ["GA4_PROPERTY_ID"]
client_email = os.environ["GA4_CLIENT_EMAIL"]
private_key = os.environ["GA4_PRIVATE_KEY"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info({
    "type": "service_account",
    "private_key": private_key,
    "client_email": client_email,
    "token_uri": "https://oauth2.googleapis.com/token",
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
        Metric(name="keyEvents"),
        Metric(name="averageSessionDuration"),
    ],
)

response = client.run_report(request)
```

Install the libraries with `pip install google-analytics-data google-auth`.

### Key dimensions for lead analysis

Names as listed in the [API schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema):

| Dimension | Description | Use case |
|-----------|-------------|----------|
| `sessionDefaultChannelGroup` | Channel classification (Paid Search, Organic Search, Organic Social, etc.) | Channel-level attribution |
| `sessionSource` | Traffic source (google, facebook, direct) | Source-level attribution |
| `sessionMedium` | Medium (cpc, organic, referral) | Medium-level analysis |
| `eventName` | Name of the event | Key-event breakdown by event |
| `pageTitle` | Page title | Content performance |
| `landingPagePlusQueryString` | Landing page path with query string | Entry-point analysis |

### Key metrics

| Metric | Description |
|--------|-------------|
| `sessions` | Number of sessions |
| `totalUsers` | Distinct users |
| `screenPageViews` | Page and screen views |
| `keyEvents` | Count of key events (formerly `conversions`) |
| `averageSessionDuration` | Average session duration, in seconds |

### Key events (formerly "conversions")

GA4 renamed conversions to **key events**. In the Data API, `conversions` was deprecated on 2024-05-06
and replaced by `keyEvents`, along with related metrics such as `sessionConversionRate` →
`sessionKeyEventRate` ([changelog](https://developers.google.com/analytics/devguides/reporting/data/v1/changelog)).

Some events, such as `first_open` and `purchase`, are marked as key events by default; you can mark any
event as a key event
([API schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema)). To see
or change them: Admin → Data display → Events, then toggle **Mark as key event**
([GA4 help](https://support.google.com/analytics/answer/12844695)).

To break key events down by event, add `Dimension(name="eventName")` to the request.

## Common errors and fixes

Google documents the API's error responses as 400, 401, 403, 429 and 500
([errors](https://developers.google.com/analytics/devguides/reporting/data/v1/errors)).

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 403 `PERMISSION_DENIED` | The service account has no access to the property, or the Data API is not enabled in the project | Add the service account email as a Viewer under Admin → Property access management; enable the API |
| 400 `INVALID_ARGUMENT` | A malformed request, such as an unknown dimension or metric name, or `conversions` on code that should now use `keyEvents` | Check names against the API schema |
| Error or no data when using a `G-XXXX` ID | A measurement ID was used instead of the numeric property ID | Use the numeric property ID from Admin → Property Settings |
| Invalid private key | Literal `\n` sequences were not converted to line breaks | Convert them once, as in the sample |
| No rows returned | The date range has no data | Check the date range and that the property collects data |

## What this is not

This is not a guide to GA4's Measurement Protocol (for sending events to GA4) or the Admin API (for
managing properties). It covers only the Data API for pulling report data.

It is also not about Universal Analytics, which the Data API does not support; Universal Analytics used
the Reporting API v4.

## References

- GA4 Data API overview: https://developers.google.com/analytics/devguides/reporting/data/v1
- Quickstart (enabling the API): https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart
- API schema (dimensions, metrics, default key events): https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
- Changelog (conversions → keyEvents): https://developers.google.com/analytics/devguides/reporting/data/v1/changelog
- Property ID: https://developers.google.com/analytics/devguides/reporting/data/v1/property-id
- Errors: https://developers.google.com/analytics/devguides/reporting/data/v1/errors
- Access management and roles: https://support.google.com/analytics/answer/9305587
- Key events: https://support.google.com/analytics/answer/12844695
- Creating service accounts: https://cloud.google.com/iam/docs/service-accounts-create
