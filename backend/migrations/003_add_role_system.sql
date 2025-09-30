-- Migration: Add role-based access control system
-- Date: 2025-09-27
-- Description: Add user roles and persistent admin document management

-- ==============================================
-- 1. ADD USER ROLES
-- ==============================================

-- Add role column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';

-- Create constraint for valid roles
ALTER TABLE users ADD CONSTRAINT chk_user_role 
    CHECK (role IN ('user', 'admin'));

-- Create index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Add comment
COMMENT ON COLUMN users.role IS 'User role: admin can upload PDFs, user can only query';

-- ==============================================
-- 2. ADMIN DOCUMENTS TABLE - Persistent Document Storage
-- ==============================================

CREATE TABLE IF NOT EXISTS admin_documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    document_hash VARCHAR(64) UNIQUE, -- To prevent duplicates
    uploaded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    processing_status VARCHAR(20) DEFAULT 'pending',
    vector_store_path TEXT,
    language VARCHAR(10) DEFAULT 'english',
    embedding_model VARCHAR(100) DEFAULT 'BAAI/bge-small-en-v1.5',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_admin_documents_status ON admin_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_admin_documents_active ON admin_documents(is_active);
CREATE INDEX IF NOT EXISTS idx_admin_documents_uploaded_by ON admin_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_admin_documents_hash ON admin_documents(document_hash);
CREATE INDEX IF NOT EXISTS idx_admin_documents_created_at ON admin_documents(created_at);

-- Constraints
ALTER TABLE admin_documents ADD CONSTRAINT chk_processing_status 
    CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'));

-- Update task type constraint to include admin tasks
ALTER TABLE user_tasks DROP CONSTRAINT IF EXISTS chk_task_type;
ALTER TABLE user_tasks ADD CONSTRAINT chk_task_type 
    CHECK (task_type IN ('pdf_processing', 'document_processing', 'data_processing', 'admin_pdf_processing'));
COMMENT ON COLUMN admin_documents.document_hash IS 'SHA-256 hash to prevent duplicate uploads';
COMMENT ON COLUMN admin_documents.vector_store_path IS 'Path to the vector store for this document';

-- ==============================================
-- 3. GLOBAL VECTOR STORE TABLE - Shared Knowledge Base
-- ==============================================

CREATE TABLE IF NOT EXISTS global_vector_store (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES admin_documents(id) ON DELETE CASCADE,
    vector_store_path TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_global_vector_store_document ON global_vector_store(document_id);
CREATE INDEX IF NOT EXISTS idx_global_vector_store_active ON global_vector_store(is_active);

-- Comments
COMMENT ON TABLE global_vector_store IS 'Global vector store for admin-uploaded documents';

-- ==============================================
-- 4. USER ACCESS LOG - Track User Interactions
-- ==============================================

CREATE TABLE IF NOT EXISTS user_access_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_access_log_user ON user_access_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_access_log_action ON user_access_log(action);
CREATE INDEX IF NOT EXISTS idx_user_access_log_created ON user_access_log(created_at);

-- Comments
COMMENT ON TABLE user_access_log IS 'Audit log for user actions and access patterns';

-- ==============================================
-- 5. UPDATE TRIGGERS
-- ==============================================

-- Trigger for admin_documents updated_at
CREATE TRIGGER update_admin_documents_updated_at 
    BEFORE UPDATE ON admin_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================
-- 6. CREATE ADMIN USER
-- ==============================================

-- Insert admin user (password: admin123 - hashed with bcrypt)
INSERT INTO users (email, password, role) 
VALUES ('admin@vitbot.com', '$2b$12$LQv3c1yqBNVVhjE5cXBGLOHcxdJHYU8QHCW6b9.3eWcnNOEn8/JfW', 'admin')
ON CONFLICT (email) DO UPDATE SET 
    role = 'admin',
    password = '$2b$12$LQv3c1yqBNVVhjE5cXBGLOHcxdJHYU8QHCW6b9.3eWcnNOEn8/JfW';

-- ==============================================
-- 7. UPDATE EXISTING USERS
-- ==============================================

-- Set all existing users (except admin) as 'user' role
UPDATE users SET role = 'user' WHERE role IS NULL AND email != 'admin@vitbot.com';

-- ==============================================
-- 8. VERIFICATION QUERIES
-- ==============================================

-- Verify admin user creation
SELECT 'Admin user created successfully' as status, 
       id, email, role, created_at 
FROM users WHERE email = 'admin@vitbot.com';

-- Count users by role
SELECT role, COUNT(*) as user_count 
FROM users 
GROUP BY role;

-- Verify new tables
SELECT 'New tables created successfully! Count: ' || COUNT(*)::text as result
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('admin_documents', 'global_vector_store', 'user_access_log');

-- Success message
SELECT '🎉 Role-based access control system setup complete!' as status;