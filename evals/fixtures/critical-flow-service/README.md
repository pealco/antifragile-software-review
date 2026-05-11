# Critical Flow Service Fixture

Use this fixture for Scenario 6. The intended critical flow is a billing charge request that writes local state, calls a billing provider, and relies on sparse operational feedback.

The reviewer should trace the billing flow before ranking findings, then score the provider-call and failure-feedback risks above unrelated low-impact issues.
