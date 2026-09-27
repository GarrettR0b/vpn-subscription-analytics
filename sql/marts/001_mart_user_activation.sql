-- Grain: one row per eligible user.
-- Business purpose: centralize the canonical VPN 7-day activation definition.

CREATE OR REPLACE VIEW analytics.mart_user_activation AS
WITH device_milestones AS (
    SELECT
        user_id,
        MIN(installed_at) AS app_installed_at
    FROM core.devices
    GROUP BY user_id
),
session_metrics AS (
    SELECT
        s.user_id,
        MIN(s.started_at) FILTER (
            WHERE s.connection_status = 'success'
        ) AS first_successful_connection_at,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS successful_sessions_7d,
        COUNT(DISTINCT DATE(s.started_at AT TIME ZONE 'UTC')) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS active_days_7d,
        COALESCE(SUM(EXTRACT(EPOCH FROM (s.ended_at - s.started_at)) / 60.0) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ), 0) AS protected_minutes_7d,
        COALESCE(SUM(s.bytes_down + s.bytes_up) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ), 0) / 1000000000.0 AS traffic_gb_7d,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'failed'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS failed_attempts_7d,
        COUNT(*) FILTER (
            WHERE s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS total_attempts_7d,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.connection_time_ms) FILTER (
            WHERE s.connection_status = 'success'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS p95_connection_time_ms,
        COUNT(*) FILTER (
            WHERE s.connection_status = 'success'
              AND s.disconnect_reason = 'network_lost'
              AND s.started_at < u.registered_at + INTERVAL '7 days'
        ) AS forced_disconnects_7d
    FROM core.vpn_sessions AS s
    JOIN core.users AS u USING (user_id)
    WHERE s.started_at >= u.registered_at
    GROUP BY s.user_id
),
experiment AS (
    SELECT
        user_id,
        MAX(variant) FILTER (
            WHERE experiment_id = 'smart_location_onboarding_v1'
        ) AS experiment_variant
    FROM core.experiment_assignments
    GROUP BY user_id
),
base AS (
    SELECT
        u.user_id,
        u.registered_at,
        u.acquisition_channel,
        u.country,
        u.signup_platform,
        sub.plan,
        sub.status AS subscription_status,
        sub.converted_at,
        dm.app_installed_at,
        sm.first_successful_connection_at,
        COALESCE(sm.successful_sessions_7d, 0) AS successful_sessions_7d,
        COALESCE(sm.active_days_7d, 0) AS active_days_7d,
        COALESCE(sm.protected_minutes_7d, 0) AS protected_minutes_7d,
        COALESCE(sm.traffic_gb_7d, 0) AS traffic_gb_7d,
        COALESCE(sm.failed_attempts_7d, 0) AS failed_attempts_7d,
        COALESCE(sm.total_attempts_7d, 0) AS total_attempts_7d,
        sm.p95_connection_time_ms,
        COALESCE(sm.forced_disconnects_7d, 0) AS forced_disconnects_7d,
        ex.experiment_variant
    FROM core.users AS u
    LEFT JOIN core.subscriptions AS sub USING (user_id)
    LEFT JOIN device_milestones AS dm USING (user_id)
    LEFT JOIN session_metrics AS sm USING (user_id)
    LEFT JOIN experiment AS ex USING (user_id)
    WHERE NOT u.is_internal
)
SELECT
    *,
    failed_attempts_7d::NUMERIC / NULLIF(total_attempts_7d, 0) AS failure_rate_7d,
    forced_disconnects_7d::NUMERIC / NULLIF(successful_sessions_7d, 0)
        AS forced_disconnect_rate_7d,
    EXTRACT(EPOCH FROM (first_successful_connection_at - registered_at)) / 3600.0
        AS time_to_first_value_hours,
    COALESCE((
        app_installed_at < registered_at + INTERVAL '7 days'
        AND successful_sessions_7d >= 3
        AND active_days_7d >= 2
        AND protected_minutes_7d >= 30
    ), FALSE) AS activated_7d
FROM base;

COMMENT ON VIEW analytics.mart_user_activation IS
    'One row per eligible VPN user with onboarding, connection-quality and 7-day activation metrics.';
