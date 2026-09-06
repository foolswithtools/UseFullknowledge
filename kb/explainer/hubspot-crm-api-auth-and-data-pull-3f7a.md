---
id: hubspot-crm-api-auth-and-data-pull-3f7a
title: "HubSpot CRM API: Authentication and Contact Data Pull"
type: explainer
summary: "How to authenticate with HubSpot's v3 CRM API using Private App Access Tokens, pull contacts with properties, and troubleshoot common errors (401, 400, 403). Includes read-only scope guidance for lead management analysis."
tags: [hubspot, crm, api, authentication, lead-management]
created_at: "2026-09-06T22:08:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4-6
updated_at: "2026-09-06T22:08:00+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [model-recall-only, primary-source-cited]
volatility: fast
sources:
  - https://developers.hubspot.com/docs/guides/api/private-apps
---

## Summary

HubSpot's v3 CRM API requires a Private App Access Token (not the deprecated API key). For read-only lead management analysis, you need the `crm.objects.contacts.read` scope. The API returns JSON with contacts and their properties.

## Context

Agents and developers integrating with HubSpot CRM to pull lead/contact data for analysis — attribution, lead drop diagnosis, conversion funnel mapping. The most common failure is using a legacy API key instead of a Private App token, resulting in HTTP 401.

## How it works

### Authentication

HubSpot has two authentication methods:

1. **API Key** (LEGACY, DEPRECATED) — Format: `xxxxx-xxxxx-xxxxx-xxxxx-xxxxx`. Does NOT work with v3 API endpoints. If your token has dashes and looks like a UUID, it's an API key. Replace it.

2. **Private App Access Token** (CURRENT) — A long alphanumeric string (no dashes). Created via HubSpot → Settings → Integrations → Private Apps → Create Private App. Required for all v3 API calls.

**For read-only lead management analysis, request these scopes:**
- `crm.objects.contacts.read` — read contacts
- `crm.objects.companies.read` — read companies (optional)
- `crm.objects.deals.read` — read deals (optional)

Do NOT request write scopes unless you need to create/update records.

### API Endpoint: List Contacts

```
GET https://api.hubapi.com/crm/v3/objects/contacts
```

**Required headers:**
```
Authorization: Bearer YOUR_PRIVATE_APP_TOKEN
Content-Type: application/json
```

**Query parameters:**
- `limit` — max 100 per page (default 10)
- `properties` — comma-separated list of property names to include
- `after` — pagination cursor from previous response

**Common properties to request:**
- `createdate` — when the contact was created
- `email` — contact email
- `firstname`, `lastname` — name
- `company` — company name
- `leadsource` — where the lead came from
- `lifecyclestage` — lead lifecycle stage (lead, MQL, SQL, opportunity, customer)

**Important:** Do NOT use `propertiesWithHistory` parameter — it causes HTTP 400 errors. Use `properties` only.

### Pagination

The API returns up to 100 contacts per page. To get all contacts:

```python
all_contacts = []
after = None
while True:
    params = {"limit": 100, "properties": "createdate,email,firstname,lastname,company,leadsource,lifecyclestage"}
    if after:
        params["after"] = after
    # ... make request ...
    all_contacts.extend(data["results"])
    after = data.get("paging", {}).get("next", {}).get("after")
    if not after:
        break
```

### Filtering by Date

The API does not support server-side date filtering for the contacts list endpoint. You must:
1. Pull all contacts (with pagination)
2. Filter client-side by the `createdate` field

```python
sep5_leads = [c for c in all_contacts if "2026-09-05" in c["properties"].get("createdate", "")]
```

### Example: Full Contact Pull

```python
import urllib.request, urllib.parse, json

token = "YOUR_PRIVATE_APP_TOKEN"
params = urllib.parse.urlencode({
    "limit": 100,
    "properties": "createdate,email,firstname,lastname,company,leadsource,lifecyclestage"
})
url = f"https://api.hubapi.com/crm/v3/objects/contacts?{params}"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
contacts = data.get("results", [])
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| HTTP 401 Unauthorized | Using API key instead of Private App token, or token expired | Create Private App, copy access token, update secret |
| HTTP 403 Forbidden | Token valid but missing required scopes | Add `crm.objects.contacts.read` scope to Private App |
| HTTP 400 Bad Request | Malformed query (e.g., `propertiesWithHistory` parameter) | Remove `propertiesWithHistory`, use `properties` only |
| HTTP 429 Too Many Requests | Rate limit exceeded (100 req/10sec for Private Apps) | Add delay between requests, use pagination |

## What this is not

This is not a guide to HubSpot's OAuth flow (for third-party apps accessing multiple HubSpot accounts). Private App tokens are for accessing your own HubSpot account. For OAuth, see HubSpot's OAuth documentation.

This is also not a guide to HubSpot's webhooks or event-based integrations. For real-time lead notifications, use HubSpot webhooks instead of polling the API.

## References

- HubSpot Private Apps: https://developers.hubspot.com/docs/guides/api/private-apps
- HubSpot CRM v3 API: https://developers.hubspot.com/docs/reference/crm/objects/contacts
- HubSpot Scopes: https://developers.hubspot.com/docs/guides/auth/scopes
