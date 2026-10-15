-- Grain: one eligible paid subscription in the simulated onboarding comparison.

CREATE OR REPLACE VIEW analytics.mart_activation_experiment AS
SELECT
    *,
    COALESCE(
        first_fetched_at < subscription_started_at + INTERVAL '7 days',
        FALSE
    ) AS link_fetched_7d
FROM analytics.mart_subscriber_activation
WHERE onboarding_variant IN ('control', 'treatment');

COMMENT ON VIEW analytics.mart_activation_experiment IS
    'Simulated comparison of the standard subscription link and a guided HAPP setup reminder.';
