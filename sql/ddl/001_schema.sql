CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS core.workspaces (
    workspace_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    acquisition_channel TEXT NOT NULL,
    country TEXT NOT NULL,
    team_size_bucket TEXT NOT NULL,
    seat_count SMALLINT NOT NULL CHECK (seat_count > 0),
    is_internal BOOLEAN NOT NULL DEFAULT FALSE,
    source_seed INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS core.users (
    user_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES core.workspaces(workspace_id),
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'agent')),
    created_at TIMESTAMPTZ NOT NULL,
    invited_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    CHECK (invited_at IS NULL OR invited_at >= created_at - INTERVAL '30 days'),
    CHECK (joined_at IS NULL OR invited_at IS NULL OR joined_at >= invited_at)
);

CREATE TABLE IF NOT EXISTS core.subscriptions (
    subscription_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL UNIQUE REFERENCES core.workspaces(workspace_id),
    plan TEXT NOT NULL CHECK (plan IN ('starter', 'growth', 'business')),
    started_at TIMESTAMPTZ NOT NULL,
    trial_ends_at TIMESTAMPTZ NOT NULL,
    converted_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('trial', 'active', 'expired', 'cancelled')),
    monthly_price_usd NUMERIC(10, 2) NOT NULL CHECK (monthly_price_usd >= 0),
    CHECK (trial_ends_at >= started_at),
    CHECK (converted_at IS NULL OR converted_at >= started_at),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

CREATE TABLE IF NOT EXISTS core.product_events (
    event_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES core.workspaces(workspace_id),
    user_id TEXT REFERENCES core.users(user_id),
    session_id TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_name TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE IF NOT EXISTS core.tickets (
    ticket_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES core.workspaces(workspace_id),
    created_by_user_id TEXT NOT NULL REFERENCES core.users(user_id),
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    channel TEXT NOT NULL CHECK (channel IN ('email', 'chat', 'web')),
    reopened_at TIMESTAMPTZ,
    csat NUMERIC(3, 2),
    CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CHECK (reopened_at IS NULL OR resolved_at IS NULL OR reopened_at >= resolved_at),
    CHECK (csat IS NULL OR (csat >= 1 AND csat <= 5))
);

CREATE TABLE IF NOT EXISTS core.ai_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES core.tickets(ticket_id),
    workspace_id TEXT NOT NULL REFERENCES core.workspaces(workspace_id),
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    edited BOOLEAN NOT NULL,
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
    cost_usd NUMERIC(12, 6) NOT NULL CHECK (cost_usd >= 0),
    CHECK (accepted_at IS NULL OR accepted_at >= created_at)
);

CREATE TABLE IF NOT EXISTS core.experiment_assignments (
    experiment_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES core.workspaces(workspace_id),
    variant TEXT NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_at TIMESTAMPTZ NOT NULL,
    stratum TEXT NOT NULL,
    PRIMARY KEY (experiment_id, workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_users_workspace
    ON core.users (workspace_id);
CREATE INDEX IF NOT EXISTS idx_events_workspace_time
    ON core.product_events (workspace_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_name_time
    ON core.product_events (event_name, occurred_at);
CREATE INDEX IF NOT EXISTS idx_tickets_workspace_time
    ON core.tickets (workspace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_suggestions_workspace_time
    ON core.ai_suggestions (workspace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_assignments_workspace
    ON core.experiment_assignments (workspace_id);

COMMENT ON SCHEMA core IS 'Synthetic source-of-truth entities for the AI SaaS portfolio project.';
COMMENT ON SCHEMA analytics IS 'Reusable business-facing data marts for notebooks and DataLens.';
