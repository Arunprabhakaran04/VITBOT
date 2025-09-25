-- Migration: Create user_tasks table for production task tracking
-- Run this script to add task tracking functionality

CREATE TABLE IF NOT EXISTS user_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    progress_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tasks_status ON user_tasks(status);
CREATE INDEX IF NOT EXISTS idx_user_tasks_created_at ON user_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_user_tasks_task_id ON user_tasks(task_id);

-- Create a constraint to ensure valid status values
ALTER TABLE user_tasks ADD CONSTRAINT chk_task_status 
    CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled'));

-- Create a constraint to ensure valid task types
ALTER TABLE user_tasks ADD CONSTRAINT chk_task_type 
    CHECK (task_type IN ('pdf_processing', 'document_processing', 'data_processing'));

-- Add a comment to the table
COMMENT ON TABLE user_tasks IS 'Tracks user task execution for production monitoring';
COMMENT ON COLUMN user_tasks.task_id IS 'Celery task ID for tracking';
COMMENT ON COLUMN user_tasks.task_type IS 'Type of task being processed';
COMMENT ON COLUMN user_tasks.status IS 'Current status of the task';
COMMENT ON COLUMN user_tasks.progress_message IS 'Current progress message from task'; 