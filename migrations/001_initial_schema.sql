-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gist; -- For compound GIST indexes

-- Drop tables if they exist (for clean migrations)
DROP TABLE IF EXISTS provider_ratings CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS zip_codes CASCADE;

-- Create ZIP codes table with geographic data
-- We'll populate this from an external source for geocoding
CREATE TABLE zip_codes (
    zip_code VARCHAR(5) PRIMARY KEY,
    city VARCHAR(100),
    state_code VARCHAR(2),
    state_name VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location GEOGRAPHY(POINT, 4326), -- PostGIS geography type
    county VARCHAR(100),
    timezone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create main providers table (matching CSV structure exactly)
CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    
    -- Provider Information (matching CSV headers)
    rndrng_prvdr_ccn VARCHAR(10), -- Changed to VARCHAR to handle any format
    rndrng_prvdr_org_name VARCHAR(255) NOT NULL,
    rndrng_prvdr_city VARCHAR(100),
    rndrng_prvdr_st TEXT, -- Street address
    rndrng_prvdr_state_fips INTEGER,
    rndrng_prvdr_zip5 VARCHAR(5), -- Keep as VARCHAR
    rndrng_prvdr_state_abrvtn VARCHAR(2),
    rndrng_prvdr_ruca DECIMAL(3,1), -- Changed to DECIMAL for float values
    rndrng_prvdr_ruca_desc TEXT,
    
    -- Medical Procedure Information
    drg_cd INTEGER NOT NULL,
    drg_desc TEXT,
    
    -- Financial Data
    tot_dschrgs INTEGER CHECK (tot_dschrgs >= 0),
    avg_submtd_cvrd_chrg DECIMAL(12,2) CHECK (avg_submtd_cvrd_chrg >= 0),
    avg_tot_pymt_amt DECIMAL(12,2) CHECK (avg_tot_pymt_amt >= 0),
    avg_mdcr_pymt_amt DECIMAL(12,2) CHECK (avg_mdcr_pymt_amt >= 0),
    
    -- Geographic data (will be populated from zip_codes table)
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location GEOGRAPHY(POINT, 4326), -- PostGIS geography column
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite unique constraint (same provider can offer multiple DRGs)
    UNIQUE(rndrng_prvdr_ccn, drg_cd)
);

-- Create provider ratings table (mock data)
CREATE TABLE provider_ratings (
    id SERIAL PRIMARY KEY,
    provider_ccn VARCHAR(10) NOT NULL,
    rating DECIMAL(3,1) NOT NULL CHECK (rating >= 1.0 AND rating <= 10.0),
    rating_category VARCHAR(50), -- 'overall', 'cleanliness', 'staff', 'comfort', etc.
    review_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite unique constraint
    UNIQUE(provider_ccn, rating_category)
);

-- Create indexes for performance

-- Geographic indexes (GIST for spatial queries)
CREATE INDEX idx_providers_location ON providers USING GIST(location);
CREATE INDEX idx_zip_codes_location ON zip_codes USING GIST(location);

-- Text search indexes (GIN for ILIKE and full-text search)
CREATE INDEX idx_providers_org_name_trgm ON providers USING GIN(rndrng_prvdr_org_name gin_trgm_ops);
CREATE INDEX idx_providers_drg_desc_trgm ON providers USING GIN(drg_desc gin_trgm_ops);

-- B-tree indexes for common queries
CREATE INDEX idx_providers_ccn ON providers(rndrng_prvdr_ccn);
CREATE INDEX idx_providers_drg_cd ON providers(drg_cd);
CREATE INDEX idx_providers_state ON providers(rndrng_prvdr_state_abrvtn);
CREATE INDEX idx_providers_zip ON providers(rndrng_prvdr_zip5);
CREATE INDEX idx_providers_charges ON providers(avg_submtd_cvrd_chrg);
CREATE INDEX idx_provider_ratings_ccn ON provider_ratings(provider_ccn);
CREATE INDEX idx_provider_ratings_rating ON provider_ratings(rating DESC);

-- Compound indexes for common query patterns
CREATE INDEX idx_providers_drg_charges ON providers(drg_cd, avg_submtd_cvrd_chrg);
CREATE INDEX idx_providers_state_drg ON providers(rndrng_prvdr_state_abrvtn, drg_cd);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_providers_updated_at BEFORE UPDATE ON providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_zip_codes_updated_at BEFORE UPDATE ON zip_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create helper function for geographic queries
CREATE OR REPLACE FUNCTION providers_within_radius(
    center_lat DECIMAL,
    center_lon DECIMAL,
    radius_km DECIMAL
)
RETURNS TABLE (
    provider_id INTEGER,
    distance_km DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        ST_Distance(
            p.location,
            ST_MakePoint(center_lon, center_lat)::geography
        ) / 1000 AS distance_km
    FROM providers p
    WHERE p.location IS NOT NULL 
    AND ST_DWithin(
        p.location,
        ST_MakePoint(center_lon, center_lat)::geography,
        radius_km * 1000  -- Convert km to meters
    )
    ORDER BY distance_km;
END;
$$ LANGUAGE plpgsql;