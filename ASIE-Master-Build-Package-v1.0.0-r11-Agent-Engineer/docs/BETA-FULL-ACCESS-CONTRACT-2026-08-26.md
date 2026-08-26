# ASIE Closed Live Beta Full-Access Contract

- **Status:** Active implementation contract
- **Baseline:** `main@a6a80fe1deeb6f81f002aa1c7d334bd364ba620b`
- **Audience:** invited beta users only

The closed live beta is free and grants the same complete feature entitlement to every invited user. Pricing and packages are not decided. The platform must not request a payment method, create a payment requirement, hide a feature behind a plan, display an upgrade prompt, auto-convert an account to paid, or apply retroactive charges.

Usage measurements exist only for observability, capacity and cost learning. Reliability, concurrency and abuse controls remain technical safeguards; they cannot become commercial quotas or an upsell surface. Provider exhaustion is an operator incident, not a user entitlement failure. A retry may be shown as scheduled only after a durable retry task identifier has been accepted; otherwise the response states honestly that no retry has been scheduled yet.

The executable source of truth is `backend/beta_access.py` and its regression suite. Existing subscription and local-invoice components remain in the repository for future separately authorized pricing work, but their HTTP mutations are fail-closed while this contract is active.
