-- Grain: one row per eligible workspace.
-- Business purpose: centralize the 7-day activation definition for Python and DataLens.

CREATE OR REPLACE VIEW analytics.mart_workspace_activation AS
WITH event_milestones AS (
    SELECT
        workspace_id,
        MIN(occurred_at) FILTER (
            WHERE event_name = 'knowledge_base_connected'
        ) AS knowledge_base_connected_at,
        MIN(occurred_at) FILTER (
            WHERE event_name = 'teammate_invited'
        ) AS teammate_invited_at
    FROM core.product_events
    GROUP BY workspace_id
),
accepted_suggestions AS (
    SELECT
        s.workspace_id,
        MIN(s.accepted_at) FILTER (
            WHERE s.accepted_at IS NOT NULL
        ) AS first_accepted_suggestion_at,
        COUNT(*) FILTER (
            WHERE s.accepted_at IS NOT NULL
              AND s.accepted_at < w.created_at + INTERVAL '7 days'
        ) AS accepted_suggestions_7d
    FROM core.ai_suggestions AS s
    JOIN core.workspaces AS w USING (workspace_id)
    GROUP BY s.workspace_id
),
experiment AS (
    SELECT
        workspace_id,
        MAX(variant) FILTER (
            WHERE experiment_id = 'guided_onboarding_v1'
        ) AS experiment_variant
    FROM core.experiment_assignments
    GROUP BY workspace_id
),
base AS (
    SELECT
        w.workspace_id,
        w.created_at,
        w.acquisition_channel,
        w.country,
        w.team_size_bucket,
        w.seat_count,
        sub.plan,
        sub.status AS subscription_status,
        em.knowledge_base_connected_at,
        em.teammate_invited_at,
        ac.first_accepted_suggestion_at,
        COALESCE(ac.accepted_suggestions_7d, 0) AS accepted_suggestions_7d,
        ex.experiment_variant
    FROM core.workspaces AS w
    LEFT JOIN core.subscriptions AS sub USING (workspace_id)
    LEFT JOIN event_milestones AS em USING (workspace_id)
    LEFT JOIN accepted_suggestions AS ac USING (workspace_id)
    LEFT JOIN experiment AS ex USING (workspace_id)
    WHERE NOT w.is_internal
)
SELECT
    *,
    EXTRACT(EPOCH FROM (first_accepted_suggestion_at - created_at)) / 3600.0
        AS time_to_first_value_hours,
    COALESCE((
        knowledge_base_connected_at < created_at + INTERVAL '7 days'
        AND teammate_invited_at < created_at + INTERVAL '7 days'
        AND accepted_suggestions_7d >= 3
        AND first_accepted_suggestion_at >= knowledge_base_connected_at
        AND first_accepted_suggestion_at >= teammate_invited_at
        AND first_accepted_suggestion_at < created_at + INTERVAL '7 days'
    ), FALSE) AS activated_7d
FROM base;

COMMENT ON VIEW analytics.mart_workspace_activation IS
    'One row per eligible workspace with ordered onboarding milestones and the canonical 7-day activation flag.';
