-- Grain: one row per new paid subscription with a complete seven-day window.

CREATE OR REPLACE VIEW analytics.mart_subscriber_activation AS
WITH period AS (
    SELECT period_start, period_end
    FROM core.dataset_periods
    LIMIT 1
),
session_metrics AS (
    SELECT
        s.subscription_id,
        MIN(s.started_at) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS first_successful_connection_at,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS successful_sessions_7d,
        COUNT(DISTINCT DATE(s.started_at AT TIME ZONE 'UTC')) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS active_days_7d,
        COALESCE(SUM(EXTRACT(EPOCH FROM (s.ended_at - s.started_at)) / 60.0) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ), 0) AS protected_minutes_7d,
        COALESCE(SUM(s.bytes_down + s.bytes_up) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ), 0) / 1000000000.0 AS traffic_gb_7d,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'failed'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS failed_attempts_7d,
        COUNT(*) FILTER (
            WHERE s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS total_attempts_7d,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.connection_time_ms) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS p95_connection_time_ms,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'success'
              AND s.disconnect_reason = 'network_lost'
              AND s.started_at < sub.starts_at + INTERVAL '7 days'
        ) AS forced_disconnects_7d
    FROM core.proxy_sessions AS s
    JOIN core.subscriptions AS sub USING (subscription_id)
    WHERE s.started_at >= sub.starts_at
    GROUP BY s.subscription_id
),
base AS (
    SELECT
        u.user_id,
        sub.subscription_id,
        u.registered_at,
        u.acquisition_channel,
        u.country,
        u.signup_source,
        sub.sales_channel,
        sub.plan,
        sub.onboarding_variant,
        sub.price_rub,
        sub.included_device_slots,
        sub.extra_device_slots,
        sub.extra_device_price_rub,
        sub.monthly_total_rub,
        sub.purchased_at,
        sub.starts_at AS subscription_started_at,
        link.issued_at AS link_issued_at,
        link.first_fetched_at,
        sm.first_successful_connection_at,
        COALESCE(sm.successful_sessions_7d, 0) AS successful_sessions_7d,
        COALESCE(sm.active_days_7d, 0) AS active_days_7d,
        COALESCE(sm.protected_minutes_7d, 0) AS protected_minutes_7d,
        COALESCE(sm.traffic_gb_7d, 0) AS traffic_gb_7d,
        COALESCE(sm.failed_attempts_7d, 0) AS failed_attempts_7d,
        COALESCE(sm.total_attempts_7d, 0) AS total_attempts_7d,
        sm.p95_connection_time_ms,
        COALESCE(sm.forced_disconnects_7d, 0) AS forced_disconnects_7d
    FROM core.subscriptions AS sub
    JOIN core.users AS u USING (user_id)
    JOIN core.subscription_links AS link USING (subscription_id, user_id)
    LEFT JOIN session_metrics AS sm USING (subscription_id)
    CROSS JOIN period AS p
    WHERE NOT u.is_internal
      AND sub.starts_at >= p.period_start
      AND sub.starts_at + INTERVAL '7 days' <= p.period_end
)
SELECT
    *,
    failed_attempts_7d::NUMERIC / NULLIF(total_attempts_7d, 0) AS failure_rate_7d,
    forced_disconnects_7d::NUMERIC / NULLIF(successful_sessions_7d, 0)
        AS forced_disconnect_rate_7d,
    EXTRACT(EPOCH FROM (first_successful_connection_at - subscription_started_at)) / 3600.0
        AS time_to_first_value_hours,
    COALESCE((
        first_fetched_at < subscription_started_at + INTERVAL '7 days'
        AND successful_sessions_7d >= 3
        AND active_days_7d >= 2
        AND protected_minutes_7d >= 30
    ), FALSE) AS activated_7d
FROM base;

COMMENT ON VIEW analytics.mart_subscriber_activation IS
    'New paid subscriptions: HAPP link fetch, proxy usage and canonical seven-day activation.';
