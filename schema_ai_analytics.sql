CREATE TABLE IF NOT EXISTS ai_recommendation_interactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    payload_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
