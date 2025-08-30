-- Database Schema Integration Tests
-- AI Resume Review Platform
-- Tests database schema integrity, constraints, and functionality

-- Test results tracking
CREATE TEMP TABLE test_results (
    test_name VARCHAR(100),
    status VARCHAR(10), -- 'PASS' or 'FAIL'
    description TEXT,
    error_message TEXT
);

-- Helper function to record test results
CREATE OR REPLACE FUNCTION record_test_result(
    p_test_name VARCHAR(100),
    p_status VARCHAR(10),
    p_description TEXT,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO test_results (test_name, status, description, error_message)
    VALUES (p_test_name, p_status, p_description, p_error_message);
END;
$$ LANGUAGE plpgsql;

-- Test helper function for assertions
CREATE OR REPLACE FUNCTION assert_equals(
    p_test_name VARCHAR(100),
    p_expected BIGINT,
    p_actual BIGINT,
    p_description TEXT
) RETURNS VOID AS $$
BEGIN
    IF p_expected = p_actual THEN
        PERFORM record_test_result(p_test_name, 'PASS', p_description);
    ELSE
        PERFORM record_test_result(p_test_name, 'FAIL', p_description, 
            'Expected: ' || p_expected || ', Got: ' || p_actual);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Test 1: Verify all required tables exist
DO $$
DECLARE
    table_count INTEGER;
    expected_tables TEXT[] := ARRAY['users', 'analysis_requests', 'analysis_results', 'prompts', 'prompt_history', 'schema_migrations'];
    current_table_name TEXT;
BEGIN
    FOREACH current_table_name IN ARRAY expected_tables LOOP
        SELECT COUNT(*) INTO table_count
        FROM information_schema.tables 
        WHERE table_name = current_table_name AND table_schema = 'public';
        
        IF table_count = 1 THEN
            PERFORM record_test_result('table_exists_' || current_table_name, 'PASS', 
                'Table ' || current_table_name || ' exists');
        ELSE
            PERFORM record_test_result('table_exists_' || current_table_name, 'FAIL', 
                'Table ' || current_table_name || ' should exist', 'Table not found');
        END IF;
    END LOOP;
END $$;

-- Test 2: Verify UUID extensions and functions
DO $$
BEGIN
    -- Test UUID generation
    IF (SELECT uuid_generate_v4() IS NOT NULL) THEN
        PERFORM record_test_result('uuid_extension', 'PASS', 'UUID extension working');
    ELSE
        PERFORM record_test_result('uuid_extension', 'FAIL', 'UUID extension should work', 'uuid_generate_v4() failed');
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('uuid_extension', 'FAIL', 'UUID extension should work', SQLERRM);
END $$;

-- Test 3: Test users table constraints and triggers
DO $$
DECLARE
    user_id UUID;
    updated_time TIMESTAMP WITH TIME ZONE;
    initial_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Insert test user
    INSERT INTO users (email, password_hash, first_name, last_name)
    VALUES ('test@example.com', 'hashed_password', 'Test', 'User')
    RETURNING id, created_at INTO user_id, initial_time;
    
    PERFORM record_test_result('user_insert', 'PASS', 'User insertion works');
    
    -- Test updated_at trigger
    PERFORM pg_sleep(1); -- Small delay to ensure timestamp difference
    UPDATE users SET first_name = 'Updated' WHERE id = user_id;
    
    SELECT updated_at INTO updated_time FROM users WHERE id = user_id;
    
    IF updated_time > initial_time THEN
        PERFORM record_test_result('user_update_trigger', 'PASS', 'Updated_at trigger works');
    ELSE
        PERFORM record_test_result('user_update_trigger', 'FAIL', 'Updated_at trigger should work', 
            'Updated time not greater than initial time');
    END IF;
    
    -- Test unique email constraint
    BEGIN
        INSERT INTO users (email, password_hash, first_name, last_name)
        VALUES ('test@example.com', 'another_hash', 'Another', 'User');
        PERFORM record_test_result('user_email_unique', 'FAIL', 'Email uniqueness should be enforced', 
            'Duplicate email was allowed');
    EXCEPTION
        WHEN unique_violation THEN
            PERFORM record_test_result('user_email_unique', 'PASS', 'Email uniqueness constraint works');
    END;
    
    -- Test role constraint
    BEGIN
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES ('invalid@example.com', 'hash', 'Invalid', 'Role', 'invalid_role');
        PERFORM record_test_result('user_role_constraint', 'FAIL', 'Role constraint should be enforced', 
            'Invalid role was allowed');
    EXCEPTION
        WHEN check_violation THEN
            PERFORM record_test_result('user_role_constraint', 'PASS', 'Role constraint works');
    END;
    
    -- Clean up
    DELETE FROM users WHERE email = 'test@example.com';
    
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('user_constraints', 'FAIL', 'User table constraints test failed', SQLERRM);
END $$;

-- Test 4: Test analysis_requests table and relationships
DO $$
DECLARE
    user_id UUID;
    request_id UUID;
BEGIN
    -- Create test user first
    INSERT INTO users (email, password_hash, first_name, last_name)
    VALUES ('analyst@example.com', 'hashed_password', 'Analyst', 'User')
    RETURNING id INTO user_id;
    
    -- Insert analysis request
    INSERT INTO analysis_requests (
        user_id, original_filename, file_path, file_size_bytes, mime_type,
        target_role, experience_level
    ) VALUES (
        user_id, 'resume.pdf', '/path/to/resume.pdf', 1024, 'application/pdf',
        'Software Engineer', 'mid'
    ) RETURNING id INTO request_id;
    
    PERFORM record_test_result('analysis_request_insert', 'PASS', 'Analysis request insertion works');
    
    -- Test foreign key constraint
    BEGIN
        INSERT INTO analysis_requests (
            user_id, original_filename, file_path, file_size_bytes, mime_type
        ) VALUES (
            uuid_generate_v4(), 'test.pdf', '/path/test.pdf', 512, 'application/pdf'
        );
        PERFORM record_test_result('analysis_request_fk', 'FAIL', 'Foreign key constraint should be enforced', 
            'Invalid user_id was allowed');
    EXCEPTION
        WHEN foreign_key_violation THEN
            PERFORM record_test_result('analysis_request_fk', 'PASS', 'Foreign key constraint works');
    END;
    
    -- Test status constraint
    BEGIN
        UPDATE analysis_requests SET status = 'invalid_status' WHERE id = request_id;
        PERFORM record_test_result('analysis_request_status', 'FAIL', 'Status constraint should be enforced', 
            'Invalid status was allowed');
    EXCEPTION
        WHEN check_violation THEN
            PERFORM record_test_result('analysis_request_status', 'PASS', 'Status constraint works');
    END;
    
    -- Clean up
    DELETE FROM users WHERE id = user_id; -- Cascade should delete requests
    
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('analysis_request_constraints', 'FAIL', 'Analysis request constraints test failed', SQLERRM);
END $$;

-- Test 5: Test analysis_results table and score constraints
DO $$
DECLARE
    user_id UUID;
    request_id UUID;
    result_id UUID;
BEGIN
    -- Create test user and request
    INSERT INTO users (email, password_hash, first_name, last_name)
    VALUES ('results@example.com', 'hashed_password', 'Results', 'User')
    RETURNING id INTO user_id;
    
    INSERT INTO analysis_requests (
        user_id, original_filename, file_path, file_size_bytes, mime_type
    ) VALUES (
        user_id, 'test_resume.pdf', '/path/test_resume.pdf', 2048, 'application/pdf'
    ) RETURNING id INTO request_id;
    
    -- Insert analysis result
    INSERT INTO analysis_results (
        request_id, overall_score, strengths, weaknesses, recommendations,
        formatting_score, content_score, keyword_optimization_score,
        ai_model_used, processing_time_ms
    ) VALUES (
        request_id, 85, 
        ARRAY['Good experience section', 'Clear formatting'],
        ARRAY['Missing keywords', 'Weak summary'],
        ARRAY['Add more technical skills', 'Improve summary'],
        90, 80, 75, 'gpt-4', 1500
    ) RETURNING id INTO result_id;
    
    PERFORM record_test_result('analysis_result_insert', 'PASS', 'Analysis result insertion works');
    
    -- Test score constraints (should fail for invalid scores)
    BEGIN
        UPDATE analysis_results SET overall_score = 150 WHERE id = result_id;
        PERFORM record_test_result('analysis_result_score_max', 'FAIL', 'Score max constraint should be enforced', 
            'Score > 100 was allowed');
    EXCEPTION
        WHEN check_violation THEN
            PERFORM record_test_result('analysis_result_score_max', 'PASS', 'Score max constraint works');
    END;
    
    BEGIN
        UPDATE analysis_results SET formatting_score = -10 WHERE id = result_id;
        PERFORM record_test_result('analysis_result_score_min', 'FAIL', 'Score min constraint should be enforced', 
            'Score < 0 was allowed');
    EXCEPTION
        WHEN check_violation THEN
            PERFORM record_test_result('analysis_result_score_min', 'PASS', 'Score min constraint works');
    END;
    
    -- Clean up
    DELETE FROM users WHERE id = user_id;
    
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('analysis_result_constraints', 'FAIL', 'Analysis result constraints test failed', SQLERRM);
END $$;

-- Test 6: Test prompts table and versioning
DO $$
DECLARE
    user_id UUID;
    prompt_id UUID;
BEGIN
    -- Create test user
    INSERT INTO users (email, password_hash, first_name, last_name)
    VALUES ('prompt@example.com', 'hashed_password', 'Prompt', 'User')
    RETURNING id INTO user_id;
    
    -- Insert prompt
    INSERT INTO prompts (
        name, description, template, prompt_type, created_by
    ) VALUES (
        'test_prompt', 'Test prompt for validation', 
        'This is a test prompt template', 'analysis', user_id
    ) RETURNING id INTO prompt_id;
    
    PERFORM record_test_result('prompt_insert', 'PASS', 'Prompt insertion works');
    
    -- Test unique name constraint
    BEGIN
        INSERT INTO prompts (
            name, template, prompt_type
        ) VALUES (
            'test_prompt', 'Another template', 'system'
        );
        PERFORM record_test_result('prompt_name_unique', 'FAIL', 'Prompt name uniqueness should be enforced', 
            'Duplicate prompt name was allowed');
    EXCEPTION
        WHEN unique_violation THEN
            PERFORM record_test_result('prompt_name_unique', 'PASS', 'Prompt name uniqueness constraint works');
    END;
    
    -- Test prompt type constraint
    BEGIN
        UPDATE prompts SET prompt_type = 'invalid_type' WHERE id = prompt_id;
        PERFORM record_test_result('prompt_type_constraint', 'FAIL', 'Prompt type constraint should be enforced', 
            'Invalid prompt type was allowed');
    EXCEPTION
        WHEN check_violation THEN
            PERFORM record_test_result('prompt_type_constraint', 'PASS', 'Prompt type constraint works');
    END;
    
    -- Clean up (delete prompts first to avoid FK constraint)
    DELETE FROM prompts WHERE created_by = user_id;
    DELETE FROM users WHERE id = user_id;
    
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('prompt_constraints', 'FAIL', 'Prompt constraints test failed', SQLERRM);
END $$;

-- Test 7: Test indexes exist
DO $$
DECLARE
    index_count INTEGER;
    expected_indexes TEXT[] := ARRAY[
        'idx_users_email',
        'idx_analysis_requests_user_id',
        'idx_analysis_requests_status',
        'idx_analysis_results_request_id',
        'idx_prompts_name'
    ];
    index_name TEXT;
BEGIN
    FOREACH index_name IN ARRAY expected_indexes LOOP
        SELECT COUNT(*) INTO index_count
        FROM pg_indexes
        WHERE indexname = index_name;
        
        IF index_count = 1 THEN
            PERFORM record_test_result('index_exists_' || index_name, 'PASS', 
                'Index ' || index_name || ' exists');
        ELSE
            PERFORM record_test_result('index_exists_' || index_name, 'FAIL', 
                'Index ' || index_name || ' should exist', 'Index not found');
        END IF;
    END LOOP;
END $$;

-- Test 8: Test default prompts are inserted
DO $$
DECLARE
    prompt_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO prompt_count
    FROM prompts
    WHERE name IN ('resume_analysis_system', 'content_analysis', 'formatting_analysis');
    
    PERFORM assert_equals('default_prompts_count', 3, prompt_count, 'Default prompts should be inserted');
END $$;

-- Test 9: Test cascade deletes work correctly
DO $$
DECLARE
    cascade_user_id UUID;
    cascade_request_id UUID;
    result_count INTEGER;
    request_count INTEGER;
BEGIN
    -- Create test data chain
    INSERT INTO users (email, password_hash, first_name, last_name)
    VALUES ('cascade@example.com', 'hashed_password', 'Cascade', 'User')
    RETURNING id INTO cascade_user_id;
    
    INSERT INTO analysis_requests (
        user_id, original_filename, file_path, file_size_bytes, mime_type
    ) VALUES (
        cascade_user_id, 'cascade_test.pdf', '/path/cascade_test.pdf', 1024, 'application/pdf'
    ) RETURNING id INTO cascade_request_id;
    
    INSERT INTO analysis_results (
        request_id, ai_model_used
    ) VALUES (
        cascade_request_id, 'test-model'
    );
    
    -- Delete user and verify cascade
    DELETE FROM users WHERE id = cascade_user_id;
    
    SELECT COUNT(*) INTO request_count FROM analysis_requests WHERE analysis_requests.user_id = cascade_user_id;
    SELECT COUNT(*) INTO result_count FROM analysis_results WHERE analysis_results.request_id = cascade_request_id;
    
    PERFORM assert_equals('cascade_delete_requests', 0, request_count, 'Analysis requests should cascade delete');
    PERFORM assert_equals('cascade_delete_results', 0, result_count, 'Analysis results should cascade delete');
    
EXCEPTION
    WHEN OTHERS THEN
        PERFORM record_test_result('cascade_delete', 'FAIL', 'Cascade delete test failed', SQLERRM);
END $$;

-- Display test results
SELECT 
    test_name,
    status,
    description,
    CASE 
        WHEN error_message IS NOT NULL THEN error_message 
        ELSE 'N/A' 
    END as error_details
FROM test_results
ORDER BY 
    CASE status WHEN 'FAIL' THEN 1 ELSE 2 END,
    test_name;

-- Summary
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM test_results), 2) as percentage
FROM test_results
GROUP BY status
ORDER BY status;

-- Clean up helper functions
DROP FUNCTION IF EXISTS record_test_result;
DROP FUNCTION IF EXISTS assert_equals;