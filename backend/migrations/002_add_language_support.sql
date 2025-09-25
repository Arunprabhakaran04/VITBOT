-- Migration: Add language support to user_vector_stores table
-- Date: 2025-09-09
-- Description: Add columns to track language and embedding model used

-- Add new columns
ALTER TABLE user_vector_stores 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'english';

ALTER TABLE user_vector_stores 
ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'BAAI/bge-small-en-v1.5';

-- Update existing records with default values
UPDATE user_vector_stores 
SET language = 'english', embedding_model = 'BAAI/bge-small-en-v1.5' 
WHERE language IS NULL OR embedding_model IS NULL;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_language 
ON user_vector_stores(language);

-- Create index for user_id and language combination
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_user_lang 
ON user_vector_stores(user_id, language);

-- Add comments to document the schema
COMMENT ON COLUMN user_vector_stores.language IS 'Language of the processed document: english';
COMMENT ON COLUMN user_vector_stores.embedding_model IS 'Embedding model used for this vector store';
