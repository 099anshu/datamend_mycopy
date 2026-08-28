ALTER TABLE datasets
    ADD COLUMN source_type VARCHAR(32) NOT NULL DEFAULT 'TSDB',
    ADD COLUMN external_id VARCHAR(255),
    ADD COLUMN profile JSONB,
    ADD COLUMN uploaded_at TIMESTAMPTZ;

CREATE UNIQUE INDEX idx_datasets_source_external_id
    ON datasets (source_type, external_id)
    WHERE external_id IS NOT NULL;
