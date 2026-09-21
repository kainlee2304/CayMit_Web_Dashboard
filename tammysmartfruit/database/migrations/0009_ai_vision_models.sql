-- ==============================================================================
-- MIGRATION: 0009_ai_vision_models.sql
-- MODULE OWNER: AIModule (Module 13)
-- DESCRIPTION: Computer Vision Model Registry, 4-Tier Guard Inference Jobs,
--              Predictions Provenance, and Human QC Review & Override Tracking.
-- ==============================================================================

-- 1. AI Models Master Table (Aggregate Root)
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    model_code VARCHAR(60) UNIQUE NOT NULL, -- YOLO11_TREE_DISEASE, VIT100_FRUIT_ID, EFFICIENTNET_PATTERN_GUARD, YOLO_FRUIT_DEFECT
    model_name VARCHAR(120) NOT NULL,
    model_architecture VARCHAR(60) NOT NULL, -- YOLOv11, ViT-Base, EfficientNet-B0
    model_purpose VARCHAR(80) NOT NULL, -- GENERAL_OBJECT_FILTER, PATTERN_GUARD, FRUIT_CLASSIFIER, DISEASE_DIAGNOSIS, QUALITY_GRADING
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. AI Model Versions Table (Weight Checksums & Deployed Releases)
CREATE TABLE ai_model_versions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    model_id UUID NOT NULL REFERENCES ai_models(id) ON DELETE RESTRICT,
    version_tag VARCHAR(40) NOT NULL, -- v1.0.0-prod, v1.1.0-retrained
    weights_storage_key VARCHAR(255) NOT NULL, -- models/weights/yolo11_best_11.pt
    weights_sha256 CHAR(64) NOT NULL, -- SHA-256 integrity hash of model binary file
    input_resolution VARCHAR(20) DEFAULT '640x640' NOT NULL,
    confidence_threshold NUMERIC(4,3) DEFAULT 0.650 NOT NULL,
    is_production_active BOOLEAN DEFAULT TRUE NOT NULL,
    deployed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UNIQUE (model_id, version_tag)
);

-- 3. AI Inference Jobs Table (Aggregate Root)
CREATE TABLE ai_inference_jobs (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    model_version_id UUID NOT NULL REFERENCES ai_model_versions(id) ON DELETE RESTRICT,
    input_media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
    job_status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, -- PENDING, PROCESSING, COMPLETED, FAILED
    execution_time_ms INT,
    overall_confidence NUMERIC(5,4),
    primary_classification VARCHAR(80),
    is_jackfruit_confirmed BOOLEAN DEFAULT FALSE NOT NULL,
    is_pest_or_disease_flagged BOOLEAN DEFAULT FALSE NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ai_inference_org ON ai_inference_jobs(organization_id);
CREATE INDEX idx_ai_inference_media ON ai_inference_jobs(input_media_asset_id);
CREATE INDEX idx_ai_inference_status ON ai_inference_jobs(job_status);

-- 4. AI Predictions Table (Detailed Layer Results & Bounding Boxes)
CREATE TABLE ai_predictions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    inference_job_id UUID NOT NULL REFERENCES ai_inference_jobs(id) ON DELETE CASCADE,
    layer_tier INT NOT NULL, -- 1: General Object, 2: Domain Pattern, 3: Fruit Identity, 4: Deep Disease/Grade
    detected_class_code VARCHAR(80) NOT NULL, -- NOT_JACKFRUIT, DURIAN, HEALTHY, STEM_BORER, FRUIT_ROT, GRADE_A
    confidence_score NUMERIC(5,4) NOT NULL,
    bounding_box_json JSONB, -- { "x_min": 120, "y_min": 85, "x_max": 450, "y_max": 510 }
    diagnosis_recommendation TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_ai_predictions_job ON ai_predictions(inference_job_id);

-- 5. Human AI Review & Override Actions Table
CREATE TABLE ai_review_actions (
    id UUID PRIMARY KEY DEFAULT generate_uuid_v7(),
    inference_job_id UUID NOT NULL REFERENCES ai_inference_jobs(id) ON DELETE RESTRICT,
    reviewed_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    review_decision VARCHAR(40) NOT NULL, -- CONFIRMED_AI, OVERRIDDEN_BY_HUMAN, REJECTED_BLURRY_PHOTO
    human_assigned_class VARCHAR(80),
    human_notes TEXT,
    reviewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_ai_reviews_job ON ai_review_actions(inference_job_id);
