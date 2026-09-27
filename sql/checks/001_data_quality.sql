-- A healthy load returns failure_count = 0 and status = PASS for every row.

WITH checks AS (
    SELECT
        'dataset_period_count' AS check_name,
        ABS(COUNT(*) - 1)::BIGINT AS failure_count
    FROM core.dataset_periods

    UNION ALL

    SELECT
        'orphan_subscriptions',
        COUNT(*)::BIGINT
    FROM core.subscriptions AS sub
    LEFT JOIN core.users AS u USING (user_id)
    WHERE u.user_id IS NULL

    UNION ALL

    SELECT
        'link_subscription_user_mismatch',
        COUNT(*)::BIGINT
    FROM core.subscription_links AS link
    JOIN core.subscriptions AS sub USING (subscription_id)
    WHERE link.user_id <> sub.user_id

    UNION ALL

    SELECT
        'payment_subscription_user_mismatch',
        COUNT(*)::BIGINT
    FROM core.payments AS pay
    JOIN core.subscriptions AS sub USING (subscription_id)
    WHERE pay.user_id <> sub.user_id

    UNION ALL

    SELECT
        'session_subscription_user_mismatch',
        COUNT(*)::BIGINT
    FROM core.proxy_sessions AS s
    JOIN core.subscriptions AS sub USING (subscription_id)
    WHERE s.user_id <> sub.user_id

    UNION ALL

    SELECT
        'invalid_session_status_or_time',
        COUNT(*)::BIGINT
    FROM core.proxy_sessions
    WHERE ended_at < started_at
       OR (connection_status = 'success' AND ended_at IS NULL)
       OR (connection_status = 'failed' AND ended_at IS NOT NULL)

    UNION ALL

    SELECT
        'sessions_outside_subscription_access',
        COUNT(*)::BIGINT
    FROM core.proxy_sessions AS s
    JOIN core.subscriptions AS sub USING (subscription_id)
    WHERE s.started_at < sub.starts_at
       OR (sub.ends_at IS NOT NULL AND s.started_at >= sub.ends_at)

    UNION ALL

    SELECT
        'activation_mart_row_mismatch',
        ABS(
            (
                SELECT COUNT(*)
                FROM core.subscriptions AS sub
                JOIN core.users AS u USING (user_id)
                CROSS JOIN core.dataset_periods AS p
                WHERE NOT u.is_internal
                  AND sub.starts_at >= p.period_start
                  AND sub.starts_at + INTERVAL '7 days' <= p.period_end
            )
            - (SELECT COUNT(*) FROM analytics.mart_subscriber_activation)
        )::BIGINT

    UNION ALL

    SELECT
        'regular_paid_users_target_mismatch',
        COUNT(*)::BIGINT
    FROM analytics.mart_monthly_business AS m
    CROSS JOIN core.dataset_periods AS p
    WHERE m.regular_paid_users <> p.regular_user_target
)
SELECT
    check_name,
    failure_count,
    CASE WHEN failure_count = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks
ORDER BY check_name;
