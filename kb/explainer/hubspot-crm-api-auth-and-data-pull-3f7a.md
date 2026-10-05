---
id: hubspot-crm-api-auth-and-data-pull-3f7a
title: "HubSpot CRM API: Authentication and Contact Data Pull"
type: explainer
summary: "How to authenticate to HubSpot's CRM API for read-only access to your own account (a service key or a legacy private app token, sent as a Bearer token; account API keys stopped working in 2022), list contacts with chosen properties and cursor pagination, filter by creation date with the Search API, and read 401, 403 and 429 errors. HubSpot now date-versions its APIs (e.g. /crm/objects/2026-09/...); the older /crm/v3/ paths still work."
tags: [hubspot, crm, api, authentication, lead-management]
created_at: "2026-09-06T22:08:00+00:00"
created_by_tool: loup
created_by_model: claude-sonnet-4-6
updated_at: "2026-10-05T00:11:34+00:00"
updated_by_kind: agent
updated_by: claude-code
review_status: unreviewed
confidence_basis: [primary-source-cited]
volatility: fast
sources:
  - https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/account-service-keys
  - https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview
  - https://developers.hubspot.com/docs/apps/legacy-apps/authentication/scopes
  - https://developers.hubspot.com/docs/developer-tooling/platform/versioning
  - https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/guide
  - https://developers.hubspot.com/docs/api-reference/latest/crm/search-the-crm
  - https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines
  - https://developers.hubspot.com/changelog/upcoming-api-key-sunset
  - https://knowledge.hubspot.com/properties/understand-traffic-source-properties
---

> **Correction notice (2026-10-04).** Rewritten after an audit against HubSpot's current documentation.
> The earlier version said a valid token is "alphanumeric, no dashes" and that a dashed token is an API
> key to replace; current tokens look like `pat-na1-xxxxxxxx-xxxx-...` and do contain dashes, so that
> advice would have had readers discard working tokens. It also said the `propertiesWithHistory`
> parameter causes HTTP 400 (it is a documented, valid parameter), that the contacts API cannot filter by
> date (the Search API can), and used `leadsource`, which is not a HubSpot default contact property. Its
> creation path, rate limits and lifecycle-stage values were out of date, and its three HubSpot links
> had stopped resolving.

## Summary

To read contacts from your own HubSpot account, create a **service key** (or a legacy private app) with
the `crm.objects.contacts.read` scope and send its token as `Authorization: Bearer <token>`. List
contacts with `GET /crm/objects/2026-09/contacts`, up to 100 per page, following the `paging.next.after`
cursor. To pull contacts created in a date range, use the Search API instead of downloading everything.

## Context

Agents and developers pulling HubSpot contact data for lead analysis: attribution, lead-volume drops,
funnel mapping. The usual failures are an old account API key (they no longer work), a token without the
right scope (403), and hitting rate limits while paginating the whole database.

## How it works

### Authentication

For read-only access to a single HubSpot account you own, HubSpot offers:

- **Service keys** (newest). In HubSpot, go to Development → Keys → Service keys → Create service key,
  then add scopes. They are meant for querying the REST APIs directly, are restricted with object scopes
  such as `crm.objects.contacts.read`, and can be rotated
  ([service keys](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/account-service-keys)).
- **Legacy private apps**, still supported: Development → Legacy apps → Create legacy app → Private
  ([legacy private apps](https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview)).
- **OAuth** with a public app, for software used across many HubSpot accounts (out of scope here).

Either token is sent the same way:

```
Authorization: Bearer pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Tokens start with `pat-` and a region code and contain dashes; HubSpot's own example shows this form.
**Account API keys** (the old `hapikey`) were sunset on November 30, 2022 and no longer work
([changelog](https://developers.hubspot.com/changelog/upcoming-api-key-sunset)).

**Scopes for read-only lead analysis**
([scopes](https://developers.hubspot.com/docs/apps/legacy-apps/authentication/scopes)):

- `crm.objects.contacts.read`: read contacts
- `crm.objects.companies.read`: read companies (optional)
- `crm.objects.deals.read`: read deals (optional)

Don't add write scopes unless you need to create or update records.

### API versions

HubSpot replaced `v1`/`v3`-style versions with date-based ones, such as `/crm/objects/2026-09/contacts`.
All the older semantically versioned APIs "are still supported and available at their previous URLs", so
`/crm/v3/objects/contacts` keeps working
([versioning](https://developers.hubspot.com/docs/developer-tooling/platform/versioning)). Check the API
reference for the current date version.

### List contacts

```
GET https://api.hubapi.com/crm/objects/2026-09/contacts?limit=100&properties=createdate,email,lifecyclestage
```

- `limit`: up to 100 contacts per request; the default is 10
  ([contacts guide](https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/guide)).
- `properties`: comma-separated property names to return.
- `after`: the cursor from the previous response's `paging.next.after`.
- `propertiesWithHistory`: also valid; it returns past values of the listed properties and lowers the
  maximum number of contacts per request.

**Useful contact properties**

- `createdate`, `email`, `firstname`, `lastname`, `company`
- `lifecyclestage`: default values are `subscriber`, `lead`, `marketingqualifiedlead`,
  `salesqualifiedlead`, `opportunity`, `customer` and `evangelist`
  ([contacts guide](https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/guide)).
- **Original Traffic Source**, the first known source through which the contact interacted with your
  business ([traffic source properties](https://knowledge.hubspot.com/properties/understand-traffic-source-properties)).
  Its internal name is `hs_analytics_source`; confirm it in your account with
  `GET /crm/properties/2026-09/0-1/hs_analytics_source`. There is no default `leadsource` property;
  that name comes from Salesforce.

### Pagination

```python
import json
import urllib.parse
import urllib.request

TOKEN = "pat-na1-..."  # from a secret, never committed
BASE = "https://api.hubapi.com/crm/objects/2026-09/contacts"
PROPS = "createdate,email,firstname,lastname,company,lifecyclestage,hs_analytics_source"

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

contacts, after = [], None
while True:
    params = {"limit": 100, "properties": PROPS}
    if after:
        params["after"] = after
    data = get(f"{BASE}?{urllib.parse.urlencode(params)}")
    contacts.extend(data.get("results", []))
    after = data.get("paging", {}).get("next", {}).get("after")
    if not after:
        break
```

### Filter by creation date with the Search API

Rather than pulling every contact and filtering locally, search on `createdate` with `BETWEEN`. Date
values are Unix epoch milliseconds, as in HubSpot's own example
([CRM search](https://developers.hubspot.com/docs/api-reference/latest/crm/search-the-crm)):

```
POST https://api.hubapi.com/crm/objects/2026-09/contacts/search
{
  "filterGroups": [{
    "filters": [{
      "propertyName": "createdate",
      "operator": "BETWEEN",
      "value": "1788566400000",
      "highValue": "1788652799999"
    }]
  }],
  "properties": ["createdate", "email", "lifecyclestage", "hs_analytics_source"],
  "limit": 200
}
```

That range is 2026-09-05 00:00:00 to 23:59:59.999 UTC. Search limits: five requests per second per
account, up to 200 results per page, and at most 10,000 results for any query; page past that with
narrower date ranges.

## Common errors and fixes

| Error | Likely cause | Fix |
|-------|-------------|-----|
| 401 Unauthorized | Missing, mistyped, rotated or deleted token, or an old account API key | Send a current service key or private app token as `Authorization: Bearer ...` |
| 403 Forbidden | Valid token without the needed scope | Add `crm.objects.contacts.read` to the key or app |
| 400 Bad Request | Malformed request, such as an invalid search body or a search body over 3,000 characters | Check the request against the API reference |
| 429 Too Many Requests | Rate limit hit | Back off and retry; for privately distributed apps HubSpot allows 100 requests per 10 seconds on Free and Starter and 190 on Professional and Enterprise, with daily caps of 250,000 to 1,000,000 by tier ([usage guidelines](https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines)). The Search API has its own limit of five requests per second |

## What this is not

This is not a guide to OAuth for apps installed in many HubSpot accounts, or to webhooks. For real-time
lead notifications, use webhooks instead of polling.

## References

- Service keys: https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/account-service-keys
- Legacy private apps: https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview
- Scopes: https://developers.hubspot.com/docs/apps/legacy-apps/authentication/scopes
- API versioning: https://developers.hubspot.com/docs/developer-tooling/platform/versioning
- Contacts API guide: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/guide
- CRM search: https://developers.hubspot.com/docs/api-reference/latest/crm/search-the-crm
- Usage guidelines (rate limits): https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines
- API key sunset: https://developers.hubspot.com/changelog/upcoming-api-key-sunset
- Traffic source properties: https://knowledge.hubspot.com/properties/understand-traffic-source-properties
