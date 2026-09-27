DROP SCHEMA IF EXISTS analytics CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;

CREATE SCHEMA core;
CREATE SCHEMA analytics;

CREATE TABLE core.dataset_periods (
    dataset_id TEXT PRIMARY KEY,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    timezone TEXT NOT NULL CHECK (timezone = 'UTC'),
    regular_user_target INTEGER NOT NULL CHECK (regular_user_target > 0),
    CHECK (period_end > period_start)
);

CREATE TABLE core.users (
    user_id TEXT PRIMARY KEY,
    registered_at TIMESTAMPTZ NOT NULL,
    acquisition_channel TEXT NOT NULL,
    country TEXT NOT NULL,
    signup_source TEXT NOT NULL CHECK (signup_source IN ('website', 'telegram_bot')),
    is_internal BOOLEAN NOT NULL DEFAULT FALSE,
    source_seed INTEGER NOT NULL
);

CREATE TABLE core.subscriptions (
    subscription_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES core.users(user_id),
    sales_channel TEXT NOT NULL CHECK (sales_channel IN ('website', 'telegram_bot')),
    plan TEXT NOT NULL CHECK (plan IN ('one_month', 'three_months', 'twelve_months')),
    purchased_at TIMESTAMPTZ NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('active', 'expired')),
    auto_renew BOOLEAN NOT NULL,
    price_rub NUMERIC(10, 2) NOT NULL CHECK (price_rub > 0),
    currency TEXT NOT NULL CHECK (currency = 'RUB'),
    CHECK (starts_at >= purchased_at),
    CHECK (ends_at IS NULL OR ends_at >= starts_at)
);

CREATE TABLE core.subscription_links (
    subscription_link_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL UNIQUE REFERENCES core.subscriptions(subscription_id),
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    issued_at TIMESTAMPTZ NOT NULL,
    first_fetched_at TIMESTAMPTZ,
    last_fetched_at TIMESTAMPTZ,
    fetch_count INTEGER NOT NULL CHECK (fetch_count >= 0),
    client_name TEXT NOT NULL CHECK (client_name = 'HAPP'),
    CHECK (first_fetched_at IS NULL OR first_fetched_at >= issued_at),
    CHECK (
        last_fetched_at IS NULL
        OR (first_fetched_at IS NOT NULL AND last_fetched_at >= first_fetched_at)
    ),
    CHECK ((first_fetched_at IS NULL) = (fetch_count = 0))
);

CREATE TABLE core.payments (
    payment_id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES core.subscriptions(subscription_id),
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    paid_at TIMESTAMPTZ NOT NULL,
    amount_rub NUMERIC(10, 2) NOT NULL CHECK (amount_rub > 0),
    currency TEXT NOT NULL CHECK (currency = 'RUB'),
    payment_type TEXT NOT NULL CHECK (payment_type IN ('initial', 'renewal')),
    payment_status TEXT NOT NULL CHECK (payment_status = 'succeeded'),
    sales_channel TEXT NOT NULL CHECK (sales_channel IN ('website', 'telegram_bot'))
);

CREATE TABLE core.proxy_servers (
    server_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    provider TEXT NOT NULL,
    capacity_mbps INTEGER NOT NULL CHECK (capacity_mbps > 0),
    monthly_cost_rub NUMERIC(10, 2) NOT NULL CHECK (monthly_cost_rub > 0),
    launched_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE core.proxy_sessions (
    proxy_session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES core.users(user_id),
    subscription_id TEXT NOT NULL REFERENCES core.subscriptions(subscription_id),
    server_id TEXT NOT NULL REFERENCES core.proxy_servers(server_id),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    connection_status TEXT NOT NULL CHECK (connection_status IN ('success', 'failed')),
    protocol TEXT NOT NULL CHECK (protocol IN ('vless', 'trojan', 'shadowsocks')),
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

CREATE INDEX idx_subscriptions_user ON core.subscriptions (user_id);
CREATE INDEX idx_links_user ON core.subscription_links (user_id);
CREATE INDEX idx_payments_subscription_time ON core.payments (subscription_id, paid_at);
CREATE INDEX idx_proxy_sessions_subscription_time
    ON core.proxy_sessions (subscription_id, started_at);
CREATE INDEX idx_proxy_sessions_server_time ON core.proxy_sessions (server_id, started_at);

COMMENT ON SCHEMA core IS
    'Synthetic sources for a VPN service sold through a website and Telegram bot and used via HAPP.';
COMMENT ON SCHEMA analytics IS 'Business-facing marts for notebooks and BI.';
