-- A healthy load returns failure_count = 0 and status = PASS for every row.

WITH checks AS (
    SELECT
        'orphan_devices' AS check_name,
        COUNT(*)::BIGINT AS failure_count
    FROM core.devices AS d
    LEFT JOIN core.users AS u USING (user_id)
    WHERE u.user_id IS NULL

    UNION ALL

    SELECT
        'events_before_registration',
        COUNT(*)::BIGINT
    FROM core.product_events AS e
    JOIN core.users AS u USING (user_id)
    WHERE e.occurred_at < u.registered_at

    UNION ALL

    SELECT
        'session_user_device_mismatch',
        COUNT(*)::BIGINT
    FROM core.vpn_sessions AS s
    JOIN core.devices AS d USING (device_id)
    WHERE s.user_id <> d.user_id

    UNION ALL

    SELECT
        'invalid_session_status_or_time',
        COUNT(*)::BIGINT
    FROM core.vpn_sessions
    WHERE ended_at < started_at
       OR (connection_status = 'success' AND ended_at IS NULL)
       OR (connection_status = 'failed' AND ended_at IS NOT NULL)

    UNION ALL

    SELECT
        'sessions_before_registration_or_install',
        COUNT(*)::BIGINT
    FROM core.vpn_sessions AS s
    JOIN core.users AS u USING (user_id)
    JOIN core.devices AS d USING (device_id)
    WHERE s.started_at < u.registered_at OR s.started_at < d.installed_at

    UNION ALL

    SELECT
        'negative_session_measures',
        COUNT(*)::BIGINT
    FROM core.vpn_sessions
    WHERE connection_time_ms < 0 OR bytes_down < 0 OR bytes_up < 0

    UNION ALL

    SELECT
        'multiple_variants_per_user',
        COUNT(*)::BIGINT
    FROM (
        SELECT experiment_id, user_id
        FROM core.experiment_assignments
        GROUP BY experiment_id, user_id
        HAVING COUNT(DISTINCT variant) > 1
    ) AS conflicts

    UNION ALL

    SELECT
        'activation_mart_row_mismatch',
        ABS(
            (SELECT COUNT(*) FROM core.users WHERE NOT is_internal)
            - (SELECT COUNT(*) FROM analytics.mart_user_activation)
        )::BIGINT
)
SELECT
    check_name,
    failure_count,
    CASE WHEN failure_count = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks
ORDER BY check_name;
