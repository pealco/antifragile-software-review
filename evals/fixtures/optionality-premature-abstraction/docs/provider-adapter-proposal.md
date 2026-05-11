# Provider Adapter Proposal

Proposal: introduce a repository-wide provider adapter around every call site.

Known evidence:

- No second provider is identified.
- No provider churn has been observed.
- The proposed boundary would touch most call sites.
- No switching metric or failure pressure is currently tracked.
