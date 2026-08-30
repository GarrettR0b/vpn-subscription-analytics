-- Each row is a check. A healthy load returns failure_count = 0 and status = PASS.

WITH checks AS (
    SELECT
        'orphan_users' AS check_name,
        COUNT(*)::BIGINT AS failure_count
    FROM core.users AS u
    LEFT JOIN core.workspaces AS w USING (workspace_id)
    WHERE w.workspace_id IS NULL

    UNION ALL

    SELECT
        'events_before_workspace',
        COUNT(*)::BIGINT
    FROM core.product_events AS e
    JOIN core.workspaces AS w USING (workspace_id)
    WHERE e.occurred_at < w.created_at

    UNION ALL

    SELECT
        'accepted_before_generated',
        COUNT(*)::BIGINT
    FROM core.ai_suggestions
    WHERE accepted_at < created_at

    UNION ALL

    SELECT
        'negative_ai_cost_or_tokens',
        COUNT(*)::BIGINT
    FROM core.ai_suggestions
    WHERE cost_usd < 0 OR input_tokens < 0 OR output_tokens < 0

    UNION ALL

    SELECT
        'multiple_variants_per_workspace',
        COUNT(*)::BIGINT
    FROM (
        SELECT experiment_id, workspace_id
        FROM core.experiment_assignments
        GROUP BY experiment_id, workspace_id
        HAVING COUNT(DISTINCT variant) > 1
    ) AS conflicts

    UNION ALL

    SELECT
        'activation_mart_row_mismatch',
        ABS(
            (SELECT COUNT(*) FROM core.workspaces WHERE NOT is_internal)
            - (SELECT COUNT(*) FROM analytics.mart_workspace_activation)
        )::BIGINT
)
SELECT
    check_name,
    failure_count,
    CASE WHEN failure_count = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks
ORDER BY check_name;
