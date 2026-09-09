---
id: acme-booking-c4-container-diagram-fa5e
title: "Acme Booking C4 container diagram"
type: diagram
summary: "C4 level 2 container diagram for the Acme Booking platform: the web app, booking API, worker and datastores, and the external payment and email providers they depend on."
tags: [c4, architecture, acme-booking]
diagram_notation: mermaid
diagram_kind: c4
c4_level: container
subject_system: acme-booking
created_at: "2026-08-14T14:21:37+00:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-09-09T17:39:20+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [synthetic-example]
volatility: slow
---

## Summary

The containers that make up the Acme Booking platform, the technology each one
runs on, and how they talk to each other. This is C4 level 2 — it stops at
deployable units and does not open any of them up.

**This is an illustrative example system, not a real client architecture.**

## Diagram

```mermaid
C4Container
    title Container diagram for Acme Booking

    Person(guest, "Guest", "Searches for and books rooms")
    Person(staff, "Front desk staff", "Manages arrivals and room changes")

    Container_Boundary(acme, "Acme Booking Platform") {
        Container(web, "Web Application", "TypeScript, Next.js", "Server-rendered booking funnel and staff console")
        Container(api, "Booking API", "Python 3.12, FastAPI", "Availability, holds, reservations, pricing rules")
        Container(worker, "Settlement Worker", "Python 3.12, Celery", "Captures payments and emits confirmations after checkout")
        ContainerDb(db, "Reservations Database", "PostgreSQL 16", "Reservations, rooms, rate plans, guest profiles")
        ContainerDb(cache, "Availability Cache", "Redis 7", "Per-property availability, recomputed on booking events")
        ContainerQueue(bus, "Event Bus", "Kafka 3.7", "Booking lifecycle events consumed by the worker")
    }

    System_Ext(pay, "Payment Gateway", "Authorizes and captures card payments")
    System_Ext(mail, "Transactional Email", "Delivers confirmations and receipts")

    Rel(guest, web, "Books rooms using", "HTTPS")
    Rel(staff, web, "Manages stays using", "HTTPS")
    Rel(web, api, "Calls", "JSON/HTTPS")
    Rel(api, db, "Reads from and writes to", "SQL/TCP")
    Rel(api, cache, "Reads availability from", "RESP/TCP")
    Rel(api, bus, "Publishes booking events to", "Kafka protocol")
    Rel(bus, worker, "Delivers events to", "Kafka protocol")
    Rel(worker, pay, "Captures payment via", "HTTPS")
    Rel(worker, mail, "Sends confirmations via", "HTTPS")
    Rel(worker, db, "Writes settlement state to", "SQL/TCP")
```

## Notes

- **Holds are not reservations.** The API writes a short-lived hold row before
  payment authorization; the worker promotes it to a reservation only after
  capture succeeds. Anything that reads reservations must ignore holds.
- **The cache is derived, never authoritative.** It is rebuilt from booking
  events, so a cold Redis costs latency but cannot lose a booking.
- Deliberately omitted at this level: the read replica behind the reporting
  path, and the CDN in front of the web application. Both belong on a
  deployment diagram rather than a container diagram.

## Related levels

Other diagrams for this system share `subject_system: acme-booking`, so the
whole C4 set can be found with:

```bash
rg -l 'subject_system: acme-booking' kb/
```
