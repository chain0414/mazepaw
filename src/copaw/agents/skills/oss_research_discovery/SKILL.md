---
name: oss_research_discovery
description: "Discover and triage open-source projects (GitHub trends, stars, curated lists) and prepare digest-ready summaries."
---

# Open-source research discovery

## Goal

Produce actionable, concise findings suitable for daily digests and follow-up tasks.

## Workflow

1. Identify sources (trending, starred repos, curated lists, newsletters) using available tools or APIs.
2. For each candidate, capture: name, one-line value, license (if relevant), activity signal, risk notes.
3. Prefer primary links (repo URL, docs) over secondary summaries.
4. Output structured bullets that can be copied into digest items or cron post-processing.

## Constraints

- Respect API rate limits and site terms.
- Do not store or echo secrets; use configured credentials only via environment or credential profiles.

## Outputs

- Shortlist of repos worth deeper review.
- Optional: suggested adoption (fork vs reference vs ignore) with rationale.
