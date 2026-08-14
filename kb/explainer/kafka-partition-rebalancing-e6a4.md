---
id: kafka-partition-rebalancing-e6a4
title: "Kafka partition rebalancing"
type: explainer
summary: "How Kafka redistributes partitions across the members of a consumer group, why the classic eager protocol stops every consumer in the group, and what cooperative incremental rebalancing changes."
tags: [kafka, consumer-groups, distributed-systems]
created_at: "2026-08-14T14:21:37+00:00"
created_by_tool: claude-code
created_by_model: claude-opus-5
updated_at: "2026-08-14T14:21:37+00:00"
updated_by_kind: agent
review_status: unreviewed
confidence_basis: [primary-source-cited]
sources:
  - "https://kafka.apache.org/documentation/#basic_ops_consumer_group"
  - "https://cwiki.apache.org/confluence/display/KAFKA/KIP-429%3A+Kafka+Consumer+Incremental+Rebalance+Protocol"
volatility: slow
---

## Summary

A Kafka topic is split into partitions, and every partition in a consumer group
is owned by exactly one consumer at a time. **Rebalancing** is the process that
decides who owns what. It runs whenever group membership or topic metadata
changes, and under the original protocol it stops consumption for the entire
group while it runs.

## Context

Consumer groups exist so that work can scale horizontally: add a consumer, and
each one handles fewer partitions. The constraint that makes this safe is that a
partition has a single owner, which is what preserves per-partition ordering.

That constraint has to be re-established whenever the set of consumers changes.
The group coordinator — a broker — triggers a rebalance when:

- a consumer joins the group;
- a consumer leaves cleanly, by sending `LeaveGroup`;
- a consumer is presumed dead, because it missed `session.timeout.ms` or blocked
  longer than `max.poll.interval.ms` between `poll()` calls;
- the number of partitions for a subscribed topic changes.

## How it works

### The eager protocol

The original protocol is *stop-the-world*:

1. The coordinator signals a rebalance by returning an error on the next
   heartbeat.
2. **Every** consumer revokes **every** partition it owns and stops fetching.
3. All members send `JoinGroup`. The coordinator picks one as group leader.
4. The leader runs the configured assignor and returns the assignment via
   `SyncGroup`.
5. Consumers resume with their new assignments.

Step 2 is the problem. A consumer that was going to keep a partition still has
to give it up and take it back, so throughput for the whole group drops to zero
for the duration — even if only one member of a fifty-member group changed.

### Why it hurts more than it looks

The stall is proportional to the slowest member, not the average. If any
consumer's `onPartitionsRevoked` callback flushes state or commits offsets
synchronously, everyone waits for it. Groups doing stateful processing therefore
experience rebalances as latency spikes across every partition at once.

A common pathology is the **rebalance storm**: a consumer is slow, misses
`max.poll.interval.ms`, gets evicted, triggers a rebalance, rejoins, and is slow
again because the rebalance itself added work. Groups can spend more time
rebalancing than consuming.

### Cooperative incremental rebalancing

KIP-429 changed the protocol so that consumers revoke only what they actually
lose. The assignment is computed over two rounds:

1. Every consumer reports what it currently owns and keeps fetching from it.
2. The leader computes the target assignment. Partitions that need to move are
   revoked — and only those.
3. A second, immediate rebalance hands the released partitions to their new
   owners.

Consumers that keep a partition never stop reading it. The cost is an extra
round trip; the benefit is that a group of fifty consumers losing one member
stops reading only the partitions that actually move.

This is enabled with the `CooperativeStickyAssignor`. Migrating an existing
group requires a two-step rolling upgrade, because a group cannot mix eager and
cooperative members: first deploy with both the old and new assignor configured,
then deploy again with only the cooperative one.

### Static membership

`group.instance.id` gives a consumer a stable identity across restarts. The
coordinator then treats a restart within `session.timeout.ms` as the *same*
member rather than a departure and an arrival, so a rolling deploy of a
stateful consumer group does not have to trigger a rebalance at all.

## What this is not

Rebalancing is not partition **reassignment**, which is a different operation
that moves partition *replicas* between brokers to balance disk and network
load. Rebalancing moves ownership between consumers and touches no data;
reassignment copies data between brokers. They share a word and nothing else.

## References

- [Kafka documentation: consumer groups](https://kafka.apache.org/documentation/#basic_ops_consumer_group)
- [KIP-429: incremental cooperative rebalancing](https://cwiki.apache.org/confluence/display/KAFKA/KIP-429%3A+Kafka+Consumer+Incremental+Rebalance+Protocol)
