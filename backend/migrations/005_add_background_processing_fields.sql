-- Migration 005: Add background processing fields to admin_documents table
-- This migration adds support for the new background processing system

-- Add task tracking and content fields to admin_documents table
ALTER TABLE admin_documents 
ADD COLUMN IF NOT EXISTS task_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS text_content TEXT,
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_admin_documents_task_id ON admin_documents(task_id);
CREATE INDEX IF NOT EXISTS idx_admin_documents_status ON admin_documents(processing_status);

-- Add comments for documentation
COMMENT ON COLUMN admin_documents.task_id IS 'Background processing task ID for tracking';
COMMENT ON COLUMN admin_documents.text_content IS 'Preview of extracted PDF text content (first 1000 chars)';
COMMENT ON COLUMN admin_documents.error_message IS 'Error message if processing failed';

-- Update any existing records to have a default status if needed
UPDATE admin_documents 
SET processing_status = 'completed' 
WHERE processing_status IS NULL AND file_path IS NOT NULL;

-- Show the updated table structure
\d admin_documents;