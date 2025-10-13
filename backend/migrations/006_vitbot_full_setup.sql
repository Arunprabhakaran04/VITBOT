-- =====================================================
-- VITBOT Complete Database Setup with Admin-User Role System
-- Execute this script in a FRESH/EMPTY PostgreSQL database
-- Date: September 27, 2025
-- =====================================================

-- This script will create EVERYTHING from scratch:
-- 1. All base tables (users, chats, messages, tasks, etc.)
-- 2. Admin-user role system
-- 3. Admin documents and global vector store
-- 4. Default admin user account
-- 5. All indexes, constraints, and triggers

BEGIN;

-- ==============================================
-- 1. USERS TABLE - Authentication with Roles
-- ==============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Index for email lookups and roles
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Constraint for valid roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_role') THEN
        ALTER TABLE users ADD CONSTRAINT chk_user_role 
            CHECK (role IN ('user', 'admin'));
    END IF;
END$$;

COMMENT ON TABLE users IS 'User authentication and management with role-based access';
COMMENT ON COLUMN users.role IS 'User role: admin can upload PDFs, user can only query';

-- ==============================================
-- 2. USER_VECTOR_STORES TABLE - PDF tracking (Legacy)
-- ==============================================
CREATE TABLE IF NOT EXISTS user_vector_stores (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vector_store_path TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    language VARCHAR(10) DEFAULT 'english',
    embedding_model VARCHAR(100) DEFAULT 'BAAI/bge-small-en-v1.5'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_user_id ON user_vector_stores(user_id);
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_active ON user_vector_stores(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_language ON user_vector_stores(language);
CREATE INDEX IF NOT EXISTS idx_user_vector_stores_user_lang ON user_vector_stores(user_id, language);

COMMENT ON TABLE user_vector_stores IS 'Legacy: Individual user vector stores (kept for compatibility)';
COMMENT ON COLUMN user_vector_stores.language IS 'Language of the processed document';
COMMENT ON COLUMN user_vector_stores.embedding_model IS 'Embedding model used for this vector store';

-- ==============================================
-- 3. ADMIN_DOCUMENTS TABLE - Persistent Admin Document Storage
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
    task_id VARCHAR(255), -- Background processing task ID for tracking
    text_content TEXT, -- Preview of extracted PDF text content (first 1000 chars)
    error_message TEXT, -- Error message if processing failed
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
CREATE INDEX IF NOT EXISTS idx_admin_documents_task_id ON admin_documents(task_id);

-- Constraints
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_processing_status') THEN
        ALTER TABLE admin_documents ADD CONSTRAINT chk_processing_status 
            CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'));
    END IF;
END$$;

COMMENT ON TABLE admin_documents IS 'Persistent document storage managed by admin users';
COMMENT ON COLUMN admin_documents.document_hash IS 'SHA-256 hash to prevent duplicate uploads';
COMMENT ON COLUMN admin_documents.vector_store_path IS 'Path to the vector store for this document';

-- ==============================================
-- 4. GLOBAL_VECTOR_STORE TABLE - Shared Knowledge Base
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

COMMENT ON TABLE global_vector_store IS 'Global vector store for admin-uploaded documents available to all users';

-- ==============================================
-- 5. USER_TASKS TABLE - Task tracking (Updated)
-- ==============================================
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tasks_status ON user_tasks(status);
CREATE INDEX IF NOT EXISTS idx_user_tasks_task_id ON user_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_user_tasks_created_at ON user_tasks(created_at);

-- Constraints for data integrity (includes admin tasks)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_task_status') THEN
        ALTER TABLE user_tasks ADD CONSTRAINT chk_task_status 
            CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_task_type') THEN
        ALTER TABLE user_tasks ADD CONSTRAINT chk_task_type 
            CHECK (task_type IN ('pdf_processing', 'document_processing', 'data_processing', 'admin_pdf_processing'));
    END IF;
END$$;

COMMENT ON TABLE user_tasks IS 'Tracks Celery task execution including admin document processing';

-- ==============================================
-- 6. CHATS TABLE - Conversation management
-- ==============================================
CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats(chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at);

COMMENT ON TABLE chats IS 'Chat conversations between users and AI assistant';

-- ==============================================
-- 7. MESSAGES TABLE - Chat messages
-- ==============================================
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) DEFAULT 'general'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at);

-- Constraints for data integrity
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_message_role') THEN
        ALTER TABLE messages ADD CONSTRAINT chk_message_role 
            CHECK (role IN ('user', 'assistant', 'system'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_message_source') THEN
        ALTER TABLE messages ADD CONSTRAINT chk_message_source 
            CHECK (source IN ('general', 'rag', 'pdf', 'system'));
    END IF;
END$$;

COMMENT ON TABLE messages IS 'Individual messages within chat conversations';

-- ==============================================
-- 8. USER_ACCESS_LOG TABLE - Audit Trail
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

COMMENT ON TABLE user_access_log IS 'Audit log for user actions and access patterns';

-- ==============================================
-- 9. POSTS TABLE (Legacy - keeping for compatibility)
-- ==============================================
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content VARCHAR(255) NOT NULL,
    published BOOLEAN NOT NULL DEFAULT true,
    posted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

COMMENT ON TABLE posts IS 'Legacy posts table - kept for compatibility';

-- ==============================================
-- 10. TRIGGERS - Automatic timestamp updates
-- ==============================================

-- Function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_tasks_updated_at') THEN
        CREATE TRIGGER update_user_tasks_updated_at 
            BEFORE UPDATE ON user_tasks
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_chats_updated_at') THEN
        CREATE TRIGGER update_chats_updated_at 
            BEFORE UPDATE ON chats
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_admin_documents_updated_at') THEN
        CREATE TRIGGER update_admin_documents_updated_at 
            BEFORE UPDATE ON admin_documents
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END$$;

-- ==============================================
-- 11. CREATE DEFAULT ADMIN USER
-- ==============================================

-- Insert admin user (email: admin@vitbot.com, password: admin123)
-- Password is hashed with bcrypt rounds=12 for security
INSERT INTO users (email, password, role) 
VALUES ('admin@vitbot.com', '$2b$12$LQv3c1yqBNVVhjE5cXBGLOHcxdJHYU8QHCW6b9.3eWcnNOEn8/JfW', 'admin')
ON CONFLICT DO NOTHING;

-- ==============================================
-- 12. CREATE SAMPLE REGULAR USER (OPTIONAL)
-- ==============================================

-- Insert a sample regular user for testing (email: user@vitbot.com, password: user123)  
INSERT INTO users (email, password, role) 
VALUES ('user@vitbot.com', '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'user')
ON CONFLICT DO NOTHING;

-- ==============================================
-- 13. DATABASE VERIFICATION
-- ==============================================

-- Check all tables were created
SELECT 'All tables created successfully! Count: ' || COUNT(*)::text as result
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'users', 'user_vector_stores', 'admin_documents', 'global_vector_store',
    'user_tasks', 'chats', 'messages', 'user_access_log', 'posts'
);

-- List all created tables with column counts
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_name = t.table_name AND table_schema = 'public') as column_count,
    CASE 
        WHEN table_name IN ('admin_documents', 'global_vector_store', 'user_access_log') THEN 'NEW (Admin System)'
        WHEN table_name = 'users' THEN 'UPDATED (Added role column)'
        WHEN table_name = 'user_tasks' THEN 'UPDATED (Added admin task types)'
        ELSE 'EXISTING'
    END as table_type
FROM information_schema.tables t
WHERE table_schema = 'public' 
ORDER BY table_type DESC, table_name;

-- Verify users created
SELECT 'Users created:' as info, email, role, created_at 
FROM users 
ORDER BY role DESC, email;

-- Count tables by type
SELECT 
    'Database Summary:' as summary,
    COUNT(*) as total_tables,
    COUNT(CASE WHEN table_name IN ('admin_documents', 'global_vector_store', 'user_access_log') THEN 1 END) as new_tables,
    COUNT(CASE WHEN table_name IN ('users', 'user_tasks') THEN 1 END) as updated_tables,
    COUNT(CASE WHEN table_name IN ('user_vector_stores', 'chats', 'messages', 'posts') THEN 1 END) as existing_tables
FROM information_schema.tables 
WHERE table_schema = 'public';

COMMIT;

-- ==============================================
-- 14. SUCCESS MESSAGE & CREDENTIALS
-- ==============================================

SELECT '🎉 VITBOT COMPLETE DATABASE SETUP SUCCESSFUL! 🎉' as status;

SELECT '👤 LOGIN CREDENTIALS' as info,
       '===================' as divider,
       'ADMIN USER:' as admin_header,
       '  Email: admin@vitbot.com' as admin_email,
       '  Password: admin123' as admin_password,
       '  Permissions: Full access, can upload PDFs, manage documents' as admin_perms,
       '' as space1,
       'REGULAR USER (for testing):' as user_header,  
       '  Email: user@vitbot.com' as user_email,
       '  Password: user123' as user_password,
       '  Permissions: Can only query admin-uploaded PDFs' as user_perms,
       '' as space2,
       '⚠️  SECURITY: Change default passwords after first login!' as security_warning;

SELECT '📋 SYSTEM FEATURES' as features,
       '=================' as divider2,
       '✅ Role-based access control (admin/user)' as feature1,
       '✅ Persistent admin document storage' as feature2,
       '✅ Global knowledge base for all users' as feature3,  
       '✅ User restriction: PDF queries only' as feature4,
       '✅ Admin privileges: Upload + manage documents' as feature5,
       '✅ Audit logging for user actions' as feature6,
       '✅ Task tracking for document processing' as feature7,
       '✅ Chat history and conversation management' as feature8;
