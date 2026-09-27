CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS core.users (
    user_id TEXT PRIMARY KEY,
    registered_at TIMESTAMPTZ NOT NULL,
    acquisition_channel TEXT NOT NULL,
    country TEXT NOT NULL,
    signup_platform TEXT NOT NULL CHECK (signup_platform IN ('android', 'ios', 'windows', 'macos')),
    is_internal BOOLEAN NOT NULL DEFAULT FALSE,
    source_seed INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS core.devices (
    device_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    platform TEXT NOT NULL CHECK (platform IN ('android', 'ios', 'windows', 'macos')),
    app_version TEXT NOT NULL,
    installed_at TIMESTAMPTZ NOT NULL,
    first_open_at TIMESTAMPTZ,
    is_primary BOOLEAN NOT NULL,
    CHECK (first_open_at IS NULL OR first_open_at >= installed_at)
);

CREATE TABLE IF NOT EXISTS core.subscriptions (
    subscription_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES core.users(user_id),
    plan TEXT NOT NULL CHECK (plan IN ('monthly', 'annual')),
    trial_started_at TIMESTAMPTZ NOT NULL,
    trial_ends_at TIMESTAMPTZ NOT NULL,
    converted_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'cancelled')),
    price_usd NUMERIC(10, 2) NOT NULL CHECK (price_usd >= 0),
    CHECK (trial_ends_at >= trial_started_at),
    CHECK (converted_at IS NULL OR converted_at >= trial_started_at),
    CHECK (ended_at IS NULL OR (converted_at IS NOT NULL AND ended_at >= converted_at))
);

CREATE TABLE IF NOT EXISTS core.product_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    device_id TEXT REFERENCES core.devices(device_id),
    session_id TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_name TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE IF NOT EXISTS core.vpn_servers (
    server_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    provider TEXT NOT NULL,
    capacity_mbps INTEGER NOT NULL CHECK (capacity_mbps > 0),
    hourly_cost_usd NUMERIC(10, 4) NOT NULL CHECK (hourly_cost_usd > 0),
    launched_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS core.vpn_sessions (
    vpn_session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    device_id TEXT NOT NULL REFERENCES core.devices(device_id),
    server_id TEXT NOT NULL REFERENCES core.vpn_servers(server_id),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    connection_status TEXT NOT NULL CHECK (connection_status IN ('success', 'failed')),
    protocol TEXT NOT NULL CHECK (protocol IN ('wireguard', 'openvpn', 'ikev2')),
    connection_time_ms INTEGER NOT NULL CHECK (connection_time_ms >= 0),
    bytes_down BIGINT NOT NULL CHECK (bytes_down >= 0),
    bytes_up BIGINT NOT NULL CHECK (bytes_up >= 0),
    disconnect_reason TEXT NOT NULL,
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    CHECK (
        (connection_status = 'success' AND ended_at IS NOT NULL)
        OR (connection_status = 'failed' AND ended_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS core.experiment_assignments (
    experiment_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    variant TEXT NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_at TIMESTAMPTZ NOT NULL,
    stratum TEXT NOT NULL,
    PRIMARY KEY (experiment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_devices_user ON core.devices (user_id);
CREATE INDEX IF NOT EXISTS idx_events_user_time ON core.product_events (user_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_name_time ON core.product_events (event_name, occurred_at);
CREATE INDEX IF NOT EXISTS idx_vpn_sessions_user_time ON core.vpn_sessions (user_id, started_at);
CREATE INDEX IF NOT EXISTS idx_vpn_sessions_server_time ON core.vpn_sessions (server_id, started_at);
CREATE INDEX IF NOT EXISTS idx_assignments_user ON core.experiment_assignments (user_id);

COMMENT ON SCHEMA core IS 'Synthetic source-of-truth entities for the VPN portfolio project.';
COMMENT ON SCHEMA analytics IS 'Business-facing marts for notebooks and DataLens.';
