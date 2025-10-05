--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13
-- Dumped by pg_dump version 15.13

-- Started on 2025-09-09 07:03:21 UTC

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS ai_resume_review_dev;
--
-- TOC entry 3563 (class 1262 OID 16384)
-- Name: ai_resume_review_dev; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE ai_resume_review_dev WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'C';


ALTER DATABASE ai_resume_review_dev OWNER TO postgres;

\connect ai_resume_review_dev

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 16385)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 3564 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 250 (class 1255 OID 16568)
-- Name: cleanup_expired_refresh_tokens(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_expired_refresh_tokens() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    deleted_count integer;
BEGIN
    -- Delete tokens that have been expired for more than 30 days
    DELETE FROM refresh_tokens 
    WHERE status = 'expired' 
    AND expires_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Also delete revoked tokens older than 7 days
    WITH revoked_delete AS (
        DELETE FROM refresh_tokens 
        WHERE status = 'revoked' 
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
        RETURNING 1
    )
    SELECT deleted_count + (SELECT COUNT(*) FROM revoked_delete) INTO deleted_count;
    
    RETURN deleted_count;
END;
$$;


ALTER FUNCTION public.cleanup_expired_refresh_tokens() OWNER TO postgres;

--
-- TOC entry 251 (class 1255 OID 16603)
-- Name: cleanup_old_file_uploads(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_old_file_uploads() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    deleted_count integer;
BEGIN
    -- Delete completed uploads older than 30 days
    DELETE FROM file_uploads 
    WHERE status = 'completed' 
    AND completed_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete failed uploads older than 7 days
    WITH error_delete AS (
        DELETE FROM file_uploads 
        WHERE status = 'error' 
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
        RETURNING 1
    )
    SELECT deleted_count + (SELECT COUNT(*) FROM error_delete) INTO deleted_count;
    
    -- Delete stuck processing uploads older than 1 day
    WITH stuck_delete AS (
        DELETE FROM file_uploads 
        WHERE status IN ('pending', 'validating', 'extracting') 
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '1 day'
        RETURNING 1
    )
    SELECT deleted_count + (SELECT COUNT(*) FROM stuck_delete) INTO deleted_count;
    
    RETURN deleted_count;
END;
$$;


ALTER FUNCTION public.cleanup_old_file_uploads() OWNER TO postgres;

--
-- TOC entry 237 (class 1255 OID 16563)
-- Name: expire_refresh_tokens(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.expire_refresh_tokens() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE refresh_tokens 
    SET status = 'expired' 
    WHERE expires_at < CURRENT_TIMESTAMP 
    AND status = 'active';
END;
$$;


ALTER FUNCTION public.expire_refresh_tokens() OWNER TO postgres;

--
-- TOC entry 252 (class 1255 OID 16604)
-- Name: get_upload_statistics(uuid); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_upload_statistics(user_id_param uuid DEFAULT NULL::uuid) RETURNS TABLE(total_uploads bigint, completed_uploads bigint, failed_uploads bigint, pending_uploads bigint, avg_processing_time_ms numeric, total_file_size_mb numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_uploads,
        COUNT(*) FILTER (WHERE status = 'completed') as completed_uploads,
        COUNT(*) FILTER (WHERE status = 'error') as failed_uploads,
        COUNT(*) FILTER (WHERE status IN ('pending', 'validating', 'extracting')) as pending_uploads,
        ROUND(AVG(processing_time), 2) as avg_processing_time_ms,
        ROUND(SUM(file_size) / (1024.0 * 1024.0), 2) as total_file_size_mb
    FROM file_uploads
    WHERE (user_id_param IS NULL OR user_id = user_id_param);
END;
$$;


ALTER FUNCTION public.get_upload_statistics(user_id_param uuid) OWNER TO postgres;

--
-- TOC entry 249 (class 1255 OID 16564)
-- Name: limit_user_sessions(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.limit_user_sessions() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Count active sessions for the user
    IF (SELECT COUNT(*) FROM refresh_tokens 
        WHERE user_id = NEW.user_id 
        AND status = 'active' 
        AND expires_at > CURRENT_TIMESTAMP) >= 3 THEN
        
        -- Revoke oldest session to make room for new one
        UPDATE refresh_tokens 
        SET status = 'revoked' 
        WHERE id = (
            SELECT id FROM refresh_tokens 
            WHERE user_id = NEW.user_id 
            AND status = 'active' 
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at ASC 
            LIMIT 1
        );
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.limit_user_sessions() OWNER TO postgres;

--
-- TOC entry 236 (class 1255 OID 16601)
-- Name: update_file_upload_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_file_upload_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_file_upload_timestamp() OWNER TO postgres;

--
-- TOC entry 235 (class 1255 OID 16502)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 218 (class 1259 OID 16412)
-- Name: analysis_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analysis_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    original_filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size_bytes integer NOT NULL,
    mime_type character varying(100) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    target_role character varying(255),
    target_industry character varying(255),
    experience_level character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT analysis_requests_experience_level_check CHECK (((experience_level)::text = ANY ((ARRAY['entry'::character varying, 'mid'::character varying, 'senior'::character varying, 'executive'::character varying])::text[]))),
    CONSTRAINT analysis_requests_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.analysis_requests OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16430)
-- Name: analysis_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analysis_results (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    request_id uuid NOT NULL,
    overall_score integer,
    strengths text[],
    weaknesses text[],
    recommendations text[],
    formatting_score integer,
    content_score integer,
    keyword_optimization_score integer,
    detailed_feedback jsonb,
    ai_model_used character varying(100) NOT NULL,
    processing_time_ms integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT analysis_results_content_score_check CHECK (((content_score >= 0) AND (content_score <= 100))),
    CONSTRAINT analysis_results_formatting_score_check CHECK (((formatting_score >= 0) AND (formatting_score <= 100))),
    CONSTRAINT analysis_results_keyword_optimization_score_check CHECK (((keyword_optimization_score >= 0) AND (keyword_optimization_score <= 100))),
    CONSTRAINT analysis_results_overall_score_check CHECK (((overall_score >= 0) AND (overall_score <= 100)))
);


ALTER TABLE public.analysis_results OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16575)
-- Name: file_uploads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.file_uploads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    filename character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    mime_type character varying(100) NOT NULL,
    file_size integer NOT NULL,
    file_hash character varying(64) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    progress integer DEFAULT 0,
    error_message text,
    target_role character varying(255),
    target_industry character varying(255),
    experience_level character varying(20),
    extracted_text text,
    word_count integer,
    character_count integer,
    extraction_method character varying(50),
    detected_sections jsonb,
    processing_time integer,
    validation_time integer,
    extraction_time integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT chk_file_uploads_experience_level CHECK ((((experience_level)::text = ANY ((ARRAY['junior'::character varying, 'mid'::character varying, 'senior'::character varying])::text[])) OR (experience_level IS NULL))),
    CONSTRAINT chk_file_uploads_file_size_positive CHECK ((file_size > 0)),
    CONSTRAINT chk_file_uploads_progress_range CHECK (((progress >= 0) AND (progress <= 100))),
    CONSTRAINT chk_file_uploads_status_values CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'validating'::character varying, 'extracting'::character varying, 'completed'::character varying, 'error'::character varying])::text[])))
);


ALTER TABLE public.file_uploads OWNER TO postgres;

--
-- TOC entry 3565 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE file_uploads; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.file_uploads IS 'Stores file upload records for resume processing with async pipeline';


--
-- TOC entry 3566 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.id IS 'Primary key for file upload record';


--
-- TOC entry 3567 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.user_id IS 'Foreign key reference to users table';


--
-- TOC entry 3568 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.filename; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.filename IS 'Stored filename (may be different from original)';


--
-- TOC entry 3569 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.original_filename; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.original_filename IS 'Original filename as uploaded by user';


--
-- TOC entry 3570 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.mime_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.mime_type IS 'MIME type detected during validation';


--
-- TOC entry 3571 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.file_size; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.file_size IS 'File size in bytes';


--
-- TOC entry 3572 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.file_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.file_hash IS 'SHA256 hash for file integrity and duplicate detection';


--
-- TOC entry 3573 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.status IS 'Processing status: pending -> validating -> extracting -> completed/error';


--
-- TOC entry 3574 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.progress; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.progress IS 'Processing progress percentage (0-100)';


--
-- TOC entry 3575 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.error_message; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.error_message IS 'Error message if processing failed';


--
-- TOC entry 3576 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.target_role; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.target_role IS 'Optional target role for resume analysis';


--
-- TOC entry 3577 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.target_industry; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.target_industry IS 'Optional target industry for resume analysis';


--
-- TOC entry 3578 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.experience_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.experience_level IS 'Optional experience level: junior, mid, senior';


--
-- TOC entry 3579 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.extracted_text; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.extracted_text IS 'Extracted text content from the file';


--
-- TOC entry 3580 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.word_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.word_count IS 'Number of words in extracted text';


--
-- TOC entry 3581 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.character_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.character_count IS 'Number of characters in extracted text';


--
-- TOC entry 3582 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.extraction_method; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.extraction_method IS 'Method used for text extraction (e.g., pdfplumber, pypdf2)';


--
-- TOC entry 3583 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.detected_sections; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.detected_sections IS 'JSON array of detected resume sections';


--
-- TOC entry 3584 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.processing_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.processing_time IS 'Total processing time in milliseconds';


--
-- TOC entry 3585 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.validation_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.validation_time IS 'File validation time in milliseconds';


--
-- TOC entry 3586 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.extraction_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.extraction_time IS 'Text extraction time in milliseconds';


--
-- TOC entry 3587 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.created_at IS 'Timestamp when upload record was created';


--
-- TOC entry 3588 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.updated_at IS 'Timestamp when record was last updated';


--
-- TOC entry 3589 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN file_uploads.completed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.file_uploads.completed_at IS 'Timestamp when processing was completed';


--
-- TOC entry 221 (class 1259 OID 16468)
-- Name: prompt_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prompt_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    prompt_id uuid NOT NULL,
    request_id uuid NOT NULL,
    prompt_version integer NOT NULL,
    prompt_content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.prompt_history OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16448)
-- Name: prompts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prompts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    template text NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    prompt_type character varying(50) NOT NULL,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT prompts_prompt_type_check CHECK (((prompt_type)::text = ANY ((ARRAY['system'::character varying, 'analysis'::character varying, 'formatting'::character varying, 'content'::character varying])::text[])))
);


ALTER TABLE public.prompts OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16537)
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.refresh_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    session_id character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    device_info text,
    ip_address character varying(45),
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_refresh_tokens_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'expired'::character varying, 'revoked'::character varying])::text[])))
);


ALTER TABLE public.refresh_tokens OWNER TO postgres;

--
-- TOC entry 3590 (class 0 OID 0)
-- Dependencies: 223
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.refresh_tokens IS 'Stores JWT refresh tokens for secure session management';


--
-- TOC entry 3591 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.id IS 'Primary key for refresh token record';


--
-- TOC entry 3592 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.user_id IS 'Foreign key reference to users table';


--
-- TOC entry 3593 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.token_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.token_hash IS 'SHA-256 hash of the JWT refresh token for security';


--
-- TOC entry 3594 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.session_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.session_id IS 'Unique session identifier for tracking multiple sessions';


--
-- TOC entry 3595 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.status IS 'Token status: active, expired, or revoked';


--
-- TOC entry 3596 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.device_info; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.device_info IS 'Optional device/browser information for session identification';


--
-- TOC entry 3597 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.ip_address; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.ip_address IS 'IP address from which the session was created';


--
-- TOC entry 3598 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.expires_at IS 'Token expiration timestamp (7 days from creation)';


--
-- TOC entry 3599 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.created_at IS 'Timestamp when token was created';


--
-- TOC entry 3600 (class 0 OID 0)
-- Dependencies: 223
-- Name: COLUMN refresh_tokens.last_used_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.refresh_tokens.last_used_at IS 'Timestamp when token was last used for refresh';


--
-- TOC entry 222 (class 1259 OID 16487)
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    version character varying(255) NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 16396)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    role character varying(50) DEFAULT 'consultant'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login_at timestamp with time zone,
    password_changed_at timestamp with time zone DEFAULT now() NOT NULL,
    failed_login_attempts integer DEFAULT 0,
    locked_until timestamp with time zone,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['consultant'::character varying, 'admin'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 3551 (class 0 OID 16412)
-- Dependencies: 218
-- Data for Name: analysis_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.analysis_requests (id, user_id, original_filename, file_path, file_size_bytes, mime_type, status, target_role, target_industry, experience_level, created_at, updated_at, completed_at) FROM stdin;
ce4e0d54-0739-49fa-8a63-eca81e80033d	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	OpenAI - Strategic Partnerships Lead.pdf	2025/09/02/4a70d24d-6d11-41f6-a97e-d87cb7b0d108.pdf	131101	application/pdf	pending	\N	\N	\N	2025-09-02 00:22:46.647512+00	2025-09-02 00:22:46.647515+00	\N
814cab5d-6186-40ac-8b6a-259815ebe8b2	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/2659a06f-dfb7-4e68-b8c4-789a68ca1e93.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 00:53:14.800173+00	2025-09-02 00:53:14.800177+00	\N
8c77aca7-59d3-4fbf-a494-c516d213061f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/fa974205-1c42-462a-88d5-64f48b33027c.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 01:01:49.973785+00	2025-09-02 01:01:49.973787+00	\N
9f46ec12-9732-4205-b3ad-12db0f3051b7	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/67594a35-87f6-4503-96f6-c7dc3b757034.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 01:03:40.119362+00	2025-09-02 01:03:40.119364+00	\N
a17d441e-40e3-4132-833f-74a9da89d200	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/c7bb39cb-c331-46f5-90ad-dbda275ba6c7.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:15:04.74138+00	2025-09-02 01:15:04.741383+00	\N
8eb8be3e-5f92-404b-ac88-bde92842f800	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/80f7c2d0-4e22-4c80-ac3d-04337a2a8d72.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:21:45.782248+00	2025-09-02 01:21:45.78225+00	\N
033526d3-4422-4ce7-8273-46e684781303	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/aa49869a-bed5-4ea6-8ad6-ccc2ae216989.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:22:16.984331+00	2025-09-02 01:22:16.984332+00	\N
2a8366db-434e-4eaa-80ee-996d6e043237	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/9dbd2a68-ecf4-4630-9cf7-38f257117389.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:27:27.585232+00	2025-09-02 01:27:27.585238+00	\N
e00512ee-3491-4e94-b259-c4aada911dae	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/baf14985-cd7e-41f8-b22e-ce2074263d80.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:27:45.033269+00	2025-09-02 01:27:45.033272+00	\N
d804a1f2-93ba-41ce-96c4-51e5043662d6	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/ada770b7-f914-4436-a40e-451738b94bb2.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 01:30:23.543857+00	2025-09-02 01:30:23.543861+00	\N
3a93ed43-f679-4d88-b196-39eb00d779d6	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/5a91ead0-766a-4cf6-afeb-b7198ce54a07.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 01:33:04.855568+00	2025-09-02 01:33:04.855572+00	\N
e02ff653-757a-43bc-acd3-58f203b49980	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/b106dfd7-3c6c-4891-ab48-59fdf60c99d6.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 01:39:59.840758+00	2025-09-02 01:39:59.84076+00	\N
f8010ea3-f551-492e-8757-6b3f74c2050a	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/135fefe1-fcc2-445c-8aa9-8864f71e48e4.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 01:52:49.845588+00	2025-09-02 01:52:49.84559+00	\N
c0ba7cc7-4c14-4f56-abda-eab0f7bb65d9	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	2025/09/02/32e3486b-9f6f-45cc-8ddd-6c049d80339f.pdf	1045136	application/pdf	pending	\N	\N	\N	2025-09-02 02:27:49.920095+00	2025-09-02 02:27:49.920097+00	\N
4a63e8b9-152c-4653-b4e8-c0e9a3ae9e9a	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/98ca0c1a-bcf4-4eb4-83e4-2c08f4c56218.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 02:27:56.629677+00	2025-09-02 02:27:56.62968+00	\N
682d6633-37b8-4599-bf68-7191481a3ee6	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	職務経歴書_稲葉安俊.pdf	2025/09/02/1b73b3b8-42af-410f-b157-481509bce497.pdf	116512	application/pdf	pending	\N	\N	\N	2025-09-02 03:41:30.528981+00	2025-09-02 03:41:30.528983+00	\N
\.


--
-- TOC entry 3552 (class 0 OID 16430)
-- Dependencies: 219
-- Data for Name: analysis_results; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.analysis_results (id, request_id, overall_score, strengths, weaknesses, recommendations, formatting_score, content_score, keyword_optimization_score, detailed_feedback, ai_model_used, processing_time_ms, created_at) FROM stdin;
\.


--
-- TOC entry 3557 (class 0 OID 16575)
-- Dependencies: 224
-- Data for Name: file_uploads; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.file_uploads (id, user_id, filename, original_filename, mime_type, file_size, file_hash, status, progress, error_message, target_role, target_industry, experience_level, extracted_text, word_count, character_count, extraction_method, detected_sections, processing_time, validation_time, extraction_time, created_at, updated_at, completed_at) FROM stdin;
8ff1f261-c220-4c7b-9e85-8a3eba946537	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	印鑑証明_福元_2025年8月21日.pdf	印鑑証明_福元_2025年8月21日.pdf	application/pdf	1045136	d392e99f55ce6d9bc847ad8fa32ed715aba0a55ca07433c2f2b303281ce5c8df	error	30	File failed security scan. Upload rejected for safety.	\N	\N	mid	\N	\N	\N	\N	\N	\N	0	\N	2025-09-03 07:03:35.408766+00	2025-09-03 07:03:35.421556+00	\N
\.


--
-- TOC entry 3554 (class 0 OID 16468)
-- Dependencies: 221
-- Data for Name: prompt_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prompt_history (id, prompt_id, request_id, prompt_version, prompt_content, created_at) FROM stdin;
\.


--
-- TOC entry 3553 (class 0 OID 16448)
-- Dependencies: 220
-- Data for Name: prompts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prompts (id, name, description, template, version, is_active, prompt_type, created_by, created_at, updated_at) FROM stdin;
de631357-25d6-48bc-84a8-c333abc0644e	resume_analysis_system	Main system prompt for resume analysis	You are an expert resume reviewer and career consultant. Analyze resumes comprehensively and provide constructive feedback.	1	t	system	\N	2025-08-30 10:13:08.584414+00	2025-08-30 10:13:08.584414+00
5a710692-d40d-4543-976a-96ed2b5dca4b	content_analysis	Prompt for analyzing resume content quality	Analyze the content of this resume for clarity, relevance, and impact. Focus on achievements, skills presentation, and overall narrative.	1	t	content	\N	2025-08-30 10:13:08.584414+00	2025-08-30 10:13:08.584414+00
b1e92597-c235-4a2d-9707-bab4fc386e9f	formatting_analysis	Prompt for analyzing resume formatting and structure	Evaluate the visual presentation, structure, and readability of this resume. Consider layout, typography, and professional appearance.	1	t	formatting	\N	2025-08-30 10:13:08.584414+00	2025-08-30 10:13:08.584414+00
\.


--
-- TOC entry 3556 (class 0 OID 16537)
-- Dependencies: 223
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.refresh_tokens (id, user_id, token_hash, session_id, status, device_info, ip_address, expires_at, created_at, last_used_at) FROM stdin;
37125b22-8bda-4f09-bab3-a1e6718b34f5	8d6ae0a3-8b47-470a-aae0-968d86449c48	c5ed71e4f3a6a97e3611bc864e855eded573a291e9a077b76edd69aad5b0b6a7	0ec334fc-9bdb-4951-ad99-e9f01cd59f93	active	testclient	testclient	2025-09-08 08:42:45.441331+00	2025-09-01 08:42:45.441309+00	2025-09-01 08:42:45.441311+00
6ec1c7c4-a813-438e-918a-337ec04b472b	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	42e316ab39dc85b99c9d8364dde4abb270336b5122a1be6360252783edc916f2	487b20c1-89b5-4c9f-aaec-2b020583f073	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:47:25.344496+00	2025-08-31 07:47:25.344485+00	2025-08-31 07:47:25.344487+00
76afb95f-2a9c-421f-a09e-fb7760686611	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	46edd321f4c15492315bc4470d5ece5d2c8323fa5f9d7da6ae725b8a11481ec3	eac8c40a-9daa-4357-a522-7bb3d6492a91	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:50:49.230732+00	2025-08-31 07:50:49.230722+00	2025-08-31 07:50:49.230723+00
29ebd109-5e5e-43bc-8eb3-2000f844315c	ce5313d9-aec9-4270-9084-82f761ea98c4	d9afe73b52df704854c7af1f4b7ce7122b5166ee84be3640a91cd264838cacb1	0016948d-b57e-4445-bb48-8e8a04fe84d0	active	testclient	testclient	2025-09-08 08:42:45.811177+00	2025-09-01 08:42:45.811168+00	2025-09-01 08:42:45.81117+00
8836011b-432d-46a8-ab07-400b213598b5	115c12e4-0b08-4f89-bcbf-0bf743985ad6	297af1dbb347e506f030b0533380a6b5182520022a2f3b18dbc8ba19f9a17925	ce47b0b9-9caf-49d9-94f9-57ed3d8ec267	active	testclient	testclient	2025-09-06 23:05:44.972069+00	2025-08-30 23:05:44.97206+00	2025-08-30 23:05:44.972062+00
9d91c426-c388-461f-b088-f587b5805f19	edea9ad1-65f1-434a-9838-9dd86a998912	a33d0c0e57b1440b0d745d0c65f8cb5086cab5cb0f937cde61f6be70e3a906c5	0c93b86a-fa77-40b8-9ce2-1267bc9f50c2	active	testclient	Unknown	2025-09-06 15:59:17.766298+00	2025-08-30 15:59:17.766288+00	2025-08-30 15:59:17.76629+00
31a56915-e021-4e82-b532-b1d4da75586f	9c7fcc1b-8cee-4817-b099-33f1562ab566	866a6402da29a2296ca7ed71ea29e90a82376c997a4286a2c960203b5a468a11	05da5555-bf8f-4593-a516-aa18247653cf	active	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 02:10:39.727838+00	2025-08-31 02:10:39.727774+00	2025-08-31 02:10:39.727776+00
c1e9225d-30f3-4f8f-9fe6-8af510f5d3a1	69ff646c-9512-4723-ae84-3391022b6a95	32912ceb50a349b52410490d06a14f2768f979f35eb2242755a8b542874af605	9e982b88-6270-4c1b-8c3e-e9f102d532c2	active	python-requests/2.31.0	127.0.0.1	2025-09-07 03:30:05.22106+00	2025-08-31 03:30:05.221039+00	2025-08-31 03:30:05.221041+00
231f36b6-6f60-4281-b28a-bd0c04622412	9c7fcc1b-8cee-4817-b099-33f1562ab566	f5d38961d79daca12b00b8a12dd41d8911a38d173b352bd9d68e04ad759763ae	89e9af2d-cb5e-455b-9826-6dd089fc7be7	active	python-requests/2.31.0	127.0.0.1	2025-09-07 03:30:05.408779+00	2025-08-31 03:30:05.408768+00	2025-08-31 03:30:05.40877+00
3335674d-cac7-4fb2-91c2-0e7ca543c575	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	3d2eeb22081bbbe4b59789e291feb281951b1ca5d3482e4f76d6de41d05e2fc3	9622ccc8-51c2-471d-9465-a81aed9141e1	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 02:31:01.7694+00	2025-08-31 02:31:01.769367+00	2025-08-31 02:31:01.76937+00
82f5fbe3-e75c-428d-87f1-a6e771064d1a	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	bf68afe7528b87ce9fcd88c30836082e9d6cc8fa0fde01031d2e94855321976f	b1f9239f-b508-44c3-a5ed-06f53483a67b	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 02:31:30.938928+00	2025-08-31 02:31:30.938919+00	2025-08-31 02:31:30.93892+00
ea511c7c-6c8e-4a2c-a32d-f1d1d4a918be	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	8026d2a874a084a42cc9066a3e27d0acadb74aa3c210b19801177386ebc6807a	c0fd28b0-638b-40ed-b88c-bb04a792d319	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:32:05.957421+00	2025-08-31 03:32:05.957412+00	2025-08-31 03:32:05.957413+00
fbdfd702-6202-4337-b88f-a433a31a64be	4053c638-306e-464c-ae15-c540fe0727fe	c41e4ee038005cdc6daa84c9b40c06c3180127fd0178f03e1416a7024c915117	a417725a-80e4-4b29-9dd6-9ceb8cb35ccd	active	testclient	Unknown	2025-09-06 16:04:16.523745+00	2025-08-30 16:04:16.523735+00	2025-08-30 16:04:16.523737+00
21470719-b0e6-410e-8169-2b13e106c556	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	9587aad8fc3cfc6b1ec9dc434c2be68080c437538e5fa09f49f731326fb84831	03fe26b2-5d3a-4de1-b639-df7f1c11ae68	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:32:17.91968+00	2025-08-31 03:32:17.91967+00	2025-08-31 03:32:17.919672+00
762bbff3-9625-4e09-90fd-e58e9cfc400b	9c7fcc1b-8cee-4817-b099-33f1562ab566	0d923a7eb2a069367ee51846d490308ebeed4b8e90feb1d590893c5680af1486	c41c097a-32cb-4020-9d2a-cf7cb6a044ae	active	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:57:53.956634+00	2025-08-31 03:57:53.956622+00	2025-08-31 03:57:53.956624+00
882ca9e5-4ee6-495b-bfcc-53e379f0b129	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	58ce2e50cc8c8a1026d70d37dd232c73181d092ea0c1323ba5b2be38c4005fa8	ecbafcb0-5489-48c4-8449-a0be94e35aa5	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:42:56.505829+00	2025-08-31 03:42:56.505768+00	2025-08-31 03:42:56.505771+00
6f90bcff-1d68-4735-ba56-821fa0001348	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	36c763cfd6e1a54511825fafaedc271447fe97279dc640aa1f47c9209bf52e84	52323a76-4ca2-4487-af13-3d56aebe6572	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:46:08.365092+00	2025-08-31 03:46:08.365082+00	2025-08-31 03:46:08.365084+00
2856febb-fa75-49a8-a609-a60b92910f86	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	6dcadb8609e47dd756c7225d603f9cc055c02f276d953c1aa7bfd41386a9bf71	813ad4ed-f25b-4d39-a904-b0c18bb53929	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 03:57:36.163958+00	2025-08-31 03:57:36.16393+00	2025-08-31 03:57:36.163931+00
2cc13ed9-33fd-473b-9f16-02986dcb5d50	40e469b0-3141-46c8-b6eb-db6518a3158e	dae1ed53e0ff951239355c8310b6e1c67d727a287a83dd406dc773b71bd3a52c	b45d31d0-41b9-4d26-a5ea-2e03ad2d8b69	active	testclient	testclient	2025-09-06 23:05:07.949098+00	2025-08-30 23:05:07.94909+00	2025-08-30 23:05:07.949092+00
7bb7a8e6-4948-4502-a652-82415e8addc4	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	8317a59823ecbbbc7dff2be309830207434aca9a0ddda3975e6c68976f85569f	6133a6df-59a4-45c8-a881-515996578884	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 06:01:01.368938+00	2025-08-31 06:01:01.368905+00	2025-08-31 06:01:01.368908+00
87d96bcc-cc59-45c0-8743-2c1dca8eda2d	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	aec3c04a5aa2782cf89a2be50dd0f43453ee52e5ef44ef523477978aac96c9d9	46a7569f-317e-455a-b3a1-9192897865f7	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 06:03:34.102523+00	2025-08-31 06:03:34.102482+00	2025-08-31 06:03:34.102484+00
3110c761-6fe6-41a8-9d01-d2f925d453b5	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	abe77a9dfeb667d89a1b0f1ce14ebd85be4785f1886ab30b42925b05131dae65	d91482e9-cb65-4ed8-b0b8-35a5d9753888	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 06:03:51.44068+00	2025-08-31 06:03:51.440667+00	2025-08-31 06:03:51.440669+00
ef6aaf70-921b-4209-9aad-79f70fb856a9	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	e394d7ae718ede105773afcdb18c776508d0ad646ee3d9600fc38496108d757c	198781e8-5722-42ed-9e64-165ed04e4d83	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:25:06.215155+00	2025-08-31 06:04:55.256401+00	2025-08-31 07:25:06.215148+00
e7ab43dc-7e69-4c16-8913-90e5b365c2b8	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	2fe0e722318e7d12531b8b5b5d16afbbd16ab08f5d68113aa49050e4a779ef87	422efcee-4346-45c8-a580-d86853583b00	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:25:35.539744+00	2025-08-31 06:05:05.23101+00	2025-08-31 07:25:35.53974+00
de4c197e-0350-47bb-ab8b-4bea71a82710	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	4130ce66f6509cba37f8644aefbd49d404defd45e93981667af705403f01174f	5c6f8d1b-1b6e-43e9-8acc-330f58d9e0ee	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:25:46.731694+00	2025-08-31 07:25:46.731682+00	2025-08-31 07:25:46.731684+00
1f701fe1-4dc3-484e-bcdc-e8d2d7c7c164	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	b300d4c7ab902e4023ce4e9ae094127840020b948e139c4a5bc6539daca21463	b27a828d-701a-4db3-ab80-6d59ee085453	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:35:33.417239+00	2025-08-31 07:35:33.417227+00	2025-08-31 07:35:33.417229+00
7ff9c06b-b272-4a8a-b6d7-ff363a37e85f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	b8e020bdd5314e4d730c4d38a34340665d3fca2aeecc6e1e7d64a7fc614ebdce	b7b9b236-3cf9-450c-9fef-b37c59bf1953	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:47:11.514406+00	2025-08-31 07:47:11.514396+00	2025-08-31 07:47:11.514397+00
0c4ab938-74d6-4640-9aaf-9670d1020a6b	79518cb6-a6d1-4795-8c83-089e9e9606d9	e8a47e3d757e0926498109868b918260f073f960cbcd2ba5c68c5c641bde37cf	8df346a7-910f-4d5c-9d94-38c59642f049	active	testclient	testclient	2025-09-08 08:42:46.167585+00	2025-09-01 08:42:46.167577+00	2025-09-01 08:42:46.167578+00
ef68af23-dcd9-4aba-bcec-df510c879966	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	501e13933d15f12004980beca508c9060c9df5a8853a5e9ab92a081588ab005c	7fff7122-b5ee-4870-a064-e91e992f899c	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-08 00:35:48.835071+00	2025-09-01 00:35:48.835007+00	2025-09-01 00:35:48.83501+00
7acce7d5-bbe8-4fcb-b9d3-094a96db2dae	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	27fe1cc388ee2a0688863d72dc56cba168326331e25d555053ebcb4bb11c897f	d855e27a-3b1d-4a05-83c3-65aea1720cf9	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 07:51:48.364049+00	2025-08-31 07:51:48.364041+00	2025-08-31 07:51:48.364042+00
64fd2f36-2823-4d10-a390-07e77c7e32fa	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	6b66a3f0e0447720fa9e9a1c98fe4c8e293f0912f4e6890e7971273ab455fec6	dfaa1a1d-7810-4da4-8649-bcb18f673a47	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-08 07:36:16.947363+00	2025-09-01 07:36:16.947342+00	2025-09-01 07:36:16.947344+00
b9a65e63-6f59-4a36-beaf-b356bf2bfddf	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	5ddea147531e74f8df6dc6fc2b96b5aaa6aacb37fe7f4ba13a868eb47a80e639	a642753b-bada-4be0-b0bb-77f28d90b7b0	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 14:13:31.046169+00	2025-08-31 14:13:31.04615+00	2025-08-31 14:13:31.046153+00
6235d214-602a-4c9b-bc26-3db28a73e46f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	aec792a34b3be46e28764f09be004af4ba3072c4621cf17c3d90b61e88e088c6	887332a9-a386-47f8-af7a-89d78f891849	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 14:23:20.184236+00	2025-08-31 14:23:20.184223+00	2025-08-31 14:23:20.184226+00
d5f6e7f2-8f1c-4abb-8a35-e657e228e003	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	aaf4d5a4045db7574ba31f9b210208616e02fc646dc3ccee46e24347afa1692f	a5d7af2a-8112-4193-9e69-5c2a6162a949	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 14:23:34.58015+00	2025-08-31 14:23:34.580141+00	2025-08-31 14:23:34.580142+00
962c7c32-7729-4d83-a226-0f75c7e3f729	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	cb4a54595ca8fa62f55e654fd05cc582c22f825dfa96d44f97e8234802015c87	bd2bc1dc-f130-4c1a-8e2e-aa2f5d7a0573	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-08 07:36:26.681032+00	2025-09-01 07:36:26.681022+00	2025-09-01 07:36:26.681024+00
06077f98-057b-4a64-ade9-699b5c22fe96	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	a90873b36d94b3a390703e827ef098c7a447aeae8428e59f7d3aae1f88303fe2	44fbe177-e5bc-43b2-8c0e-5510f02b1a1d	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 12:20:25.319797+00	2025-09-01 12:20:25.319787+00	2025-09-01 12:20:25.319791+00
5baa7f4c-33ed-41dd-a013-c83a83ec466e	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	cb1728b020cf87b527ad301cbdd6eb5a36ac9d756e46737ea57be1c17106efb2	3d550183-4898-4e42-8139-83504c4c66bb	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 12:21:14.143698+00	2025-09-01 12:21:14.143687+00	2025-09-01 12:21:14.143689+00
824815aa-de0d-475f-86f5-c2ed5fe0f611	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	c1931d3b04119b8cede767b5ef5c0a6d299ea4fca9c21602db8922adf1377dca	e1fddd94-dc7b-4cfb-a9b3-d0f793328cf2	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 12:28:22.298784+00	2025-09-01 12:28:22.298774+00	2025-09-01 12:28:22.298776+00
9d772d84-29a2-4303-95b7-aa69d6453501	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	ef08d42d8dc8a47db6d097e04c75201ad51e45422a237f318c80285e6fc8bc0a	c2733b11-dacc-4438-a268-51ccf4e7fac6	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 14:57:07.862773+00	2025-09-01 14:57:07.862601+00	2025-09-01 14:57:07.862604+00
4a11aaaf-7d48-403e-a2da-37a83c2d733d	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	574313bd53abfff4c870c6cd8f4ae6ada0e2f1589f8f912d39b9bec2ecc7df94	72b36f17-2aa2-4a3c-a6da-8cd7243be810	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 14:59:52.895314+00	2025-09-01 14:59:52.895163+00	2025-09-01 14:59:52.895164+00
eb5751be-0c54-4884-92c0-56bd50d64c7f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	c5af9ca16faee3a2ff64e503e22d23bce7f5d047c853ce231421b2dd48ec55fb	1b418036-2e0a-42d7-9659-26a91f82889c	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 23:41:03.009564+00	2025-09-01 22:46:58.728205+00	2025-09-01 23:41:03.009559+00
dcf432e6-f459-464e-991f-f57bf7549887	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	748c4fcf83e90bb505644601bc34f1c3d021a7e4ee964fc1068af01fcedac2ae	c996ee3b-319c-4d4f-8ba0-445da4b96508	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-08 23:41:45.909059+00	2025-09-01 23:41:45.909037+00	2025-09-01 23:41:45.90904+00
48efc905-f810-4ac9-81bf-b29b616764d3	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	f46faaf7687c8d48769b9275e8b70077b9eb79e95d64c4f8df5b8591801d690a	ce0c6a4b-916b-4f14-a2b6-d516334f20c4	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 00:12:40.558585+00	2025-09-02 00:12:40.558521+00	2025-09-02 00:12:40.558524+00
7cecb193-2e65-4d8b-b70f-54913193d7d6	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	79a83f7bdd5c51be433bdb4908a8992b651bc3773b4374e36cb3482651038e99	3309de27-cc3b-4563-9f28-bc7212f072b3	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 00:52:43.758311+00	2025-09-02 00:22:36.509014+00	2025-09-02 00:52:43.758308+00
d35a7827-2ab1-4c59-a2f3-2c03b27b88ec	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	10fe51b52562fe79cd8b31c3a5e9fe6bbc796a0a8655932e8638b2b0103f6aee	a4c2c577-3563-47f2-b1cb-0cdb5df5b67f	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 00:52:50.301002+00	2025-09-02 00:52:50.300984+00	2025-09-02 00:52:50.300988+00
de1f7262-9622-473f-a490-51036ca0fa53	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	f019f91fa60d2475d2a7278c891b206248456d1b4ba8a97d4157b0a8ce14f069	5ebd1470-3e82-44d2-be45-f1252b93214f	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 14:26:29.191373+00	2025-08-31 14:26:29.19136+00	2025-08-31 14:26:29.191362+00
5dfdebbb-e0aa-4e47-a609-ab6b50fd510a	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	79f07daacf83cb8c98c49bbd7c99a64d16f9bf2792ed7401be523aecdc535af8	16027dff-c4ff-4e7a-a692-73007e28774f	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	127.0.0.1	2025-09-07 14:56:06.79465+00	2025-08-31 14:56:06.794627+00	2025-08-31 14:56:06.794629+00
1796691e-94b4-44a7-b1de-444cfe4bbee0	a668a677-43b5-4393-90f0-3cb773e85af8	a1b96c300f0bd1f51affda1b23ea2b4122f0a3a96da1914abc676f86ab509090	407ada68-1ef6-4fef-bbaa-5a2d8edc9fb5	active	testclient	testclient	2025-09-08 08:40:16.49191+00	2025-09-01 08:40:16.491892+00	2025-09-01 08:40:16.491895+00
1486f704-9af5-4451-83f3-efd7d4c1a29e	8eefec12-4b00-4792-9941-0c218f2efd8e	16c6914726611fd9309ee3a978915ff02936617d57f6df29351600b17b34baf6	96a1e516-e350-43e0-89de-12f44f4e0dd5	active	testclient	testclient	2025-09-08 08:40:26.25196+00	2025-09-01 08:40:26.251941+00	2025-09-01 08:40:26.251943+00
d17fd374-b57a-4f00-87da-5a570ce88447	fd891ad5-9ac4-45f5-a7c3-54a93cf84338	49bcfdb4224c4e125a39b6942e1f010481b6108ab38b78da223beadd9673815d	669886bd-b4f1-4e8b-911f-d7569e3842bf	active	testclient	testclient	2025-09-08 08:40:26.62142+00	2025-09-01 08:40:26.621403+00	2025-09-01 08:40:26.621404+00
e42c0ecc-cc62-47bb-909d-8c47d63c0ade	ad85b2ec-60da-4d83-a361-728584b24e30	86ade0701c8be354b2afb288f3bb79f1e76dc0e53c1c80258e3b3def3d0c7068	9c91dede-b1a8-4385-a0ed-c993cd3cea16	active	testclient	testclient	2025-09-08 08:40:26.987278+00	2025-09-01 08:40:26.987269+00	2025-09-01 08:40:26.98727+00
cb3fe822-2ffa-4a0d-ad3d-17bafc21dc2c	60d41dfa-7ac7-4171-bf4f-58f0683809f0	e513f5b4f16e4afeaa3cdb913d7dcf54a49acf54db7f10d778e5605b8794828c	f0c0c448-b6f3-43ed-8c62-b358d0cdfbcb	active	testclient	testclient	2025-09-08 08:40:27.34376+00	2025-09-01 08:40:27.343751+00	2025-09-01 08:40:27.343752+00
938c1818-43c5-4a00-8b7c-65917f3e5906	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	5abae6380ad54dd5b007410e407482ad8c7e9098dc1b78644e119e21c9b81468	41fde3b0-2e91-46d0-9a06-fd9184cbaefd	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 00:53:06.710925+00	2025-09-02 00:53:06.710897+00	2025-09-02 00:53:06.710899+00
e3de494b-e6e3-4122-8cbc-094053c2315c	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	18368b99e7252aed5b3dd83c6f9847a431ca848c582eaaa431676b808f0f53b5	472a82a9-f0c8-4b35-b2ba-8f244b5cba78	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 01:01:44.575841+00	2025-09-02 01:01:44.575746+00	2025-09-02 01:01:44.575749+00
18e81dea-9162-4063-a771-fe4500e0cc13	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	14de6bcbad7c6e1776535eb07b0777b86b2ac5aa0793b494d5cf7d882ffc0275	2d1cc78f-3599-4d06-853a-bd06d14f48c9	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 03:41:22.893306+00	2025-09-02 01:21:40.073738+00	2025-09-02 03:41:22.893302+00
d4537fa6-014a-48fe-8a79-0d3b73758ced	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	f9fd378a73aac3e3d398ccf22916422f979a739e66866e1a95436033500bf451	4878bd6d-a598-4918-b236-b1761f664364	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 01:22:06.365253+00	2025-09-02 01:22:06.365214+00	2025-09-02 01:22:06.365217+00
bab4ae0b-3011-4cd0-8fff-3bb008c212ab	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	da33b77c06e086d14d8ee4f9ee49e20b572b20555d9ed2c6f8e18d51f7592bfa	b33231ab-f92c-4fe7-bfba-ac6465aab6cb	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 01:27:37.5086+00	2025-09-02 01:27:37.508542+00	2025-09-02 01:27:37.508545+00
202f3125-7134-4c58-b8af-a93f69544c74	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	041b5082af56b25c89c60f91b1e03a2aa9e61c32f25bfb4b2615d9baceca1c53	96c9237f-a311-44ab-864d-0fe8ac22c685	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 09:32:31.346085+00	2025-09-02 09:32:31.346071+00	2025-09-02 09:32:31.346074+00
0149148d-df9e-45a1-8c49-cfaf85ede476	8955190d-e058-43ce-8260-fe5481dbb6e9	1bbf5eb5f25144dee46de556356c2c80ef26e648a7143bfe4b03a52fad2fbf4f	f98714d5-9010-41e7-9058-211aad249eb6	active	curl/8.7.1	172.66.0.243	2025-09-10 03:17:42.656482+00	2025-09-03 03:17:42.656463+00	2025-09-03 03:17:42.656465+00
b614f41f-7483-45ef-afea-0fc66c529cea	8955190d-e058-43ce-8260-fe5481dbb6e9	5aa942cf100d8f8cb7abed5705f485928e1d0a2f30b505dbc03b67ffbef13e4b	972b9151-9ad4-4e01-bd48-40804acedf04	revoked	curl/8.7.1	172.66.0.243	2025-09-10 01:27:11.642045+00	2025-09-03 01:27:11.642024+00	2025-09-03 01:27:11.642026+00
55cbcb95-79a9-4ae5-958d-78f3d28e2e10	8955190d-e058-43ce-8260-fe5481dbb6e9	a73f8828133e4158e5e4f2b9de83384064823c4026a83e40c7408370107dcbee	33e0a202-f2a1-4de1-ac8b-e57884259833	active	curl/8.7.1	172.66.0.243	2025-09-10 03:19:24.693101+00	2025-09-03 03:19:24.693093+00	2025-09-03 03:19:24.693095+00
3da5ecb3-7bb1-4721-bfde-1cd6efc3b2cf	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	063a36d123b33c6fafcf71bba578cf98bcb71f59ae9ded9f1bac3e26b3ba8a2f	a6de7dba-481c-4d78-a351-65767df28133	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 14:24:03.020466+00	2025-09-02 10:02:41.816182+00	2025-09-02 14:24:03.020464+00
f8774857-5c90-436d-94a8-cf05d7b6b88a	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	049f272d3070b4b0b3617014f7fef3bee3df5d261c0d5f0121842c0aedd634b8	5cf8fe8f-b3e8-4d7d-a398-6653be5557e3	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-09 14:37:47.367762+00	2025-09-02 14:37:47.367754+00	2025-09-02 14:37:47.367757+00
192e451f-f390-4614-b278-377fe9c2dffc	8955190d-e058-43ce-8260-fe5481dbb6e9	3ca6b9ae052c3f0af1a4c730de053f3e0a432475828d8df2fa24fa9c48704729	79e63a3d-ed2d-4c67-beb6-f59924dcb6c2	revoked	curl/8.7.1	172.66.0.243	2025-09-10 01:28:50.660928+00	2025-09-03 01:28:50.660911+00	2025-09-03 01:28:50.660913+00
fd926c84-4bcb-4020-b396-24dfcbf55d0c	8955190d-e058-43ce-8260-fe5481dbb6e9	031caf0654b4b4dba79cd83edab2a307e211e48175eaae8a5b2aecf12737d03d	8d10636c-8bc4-4a18-ab8e-874a8771e10c	active	curl/8.7.1	172.66.0.243	2025-09-10 03:20:54.174189+00	2025-09-03 03:20:54.174168+00	2025-09-03 03:20:54.174171+00
a47e5d15-a3c7-49c6-84a0-599b16674671	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	34e34c9a0d82fc7c7c04a1c400ef2152b8f8e5c2b5a8813d3533754ae9f373e9	26b14dcc-8bd3-487b-9c31-f24d9b860d82	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-10 03:19:59.984034+00	2025-09-03 01:24:31.800024+00	2025-09-03 03:19:59.98403+00
f24861ec-68b9-4d02-852c-70bac1f71fcb	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	522b09416af59138ee2873679f6cca651910f90da5d67ab8649e86c71054d422	27bc65f3-cacb-4f4d-8762-91982c86178f	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-10 03:20:11.633505+00	2025-09-03 03:20:11.633499+00	2025-09-03 03:20:11.633501+00
62b25ee6-d740-40b6-a358-577e62566b62	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	49032f2dda4b699fe2db530f2baff5090f887d807006dfbf1477828a0eb343c9	ca5b8e78-fcc8-4a37-a9ce-19a42875a952	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-10 08:38:16.420409+00	2025-09-03 03:20:21.170918+00	2025-09-03 08:38:16.420407+00
6072a2aa-dc5d-4399-bc26-8600a3b55bfc	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	57fb99986b079b1c04b36c48f1f1f902a9070227d263ecd34321f5dbabf8f62c	1f559fdf-dffb-475f-aa3d-7b65609633b0	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-11 08:44:55.953817+00	2025-09-03 08:38:54.728897+00	2025-09-04 08:44:55.953815+00
f95b2777-789d-47f7-b389-635f1fb4e07c	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	64adadafba4308c3c1b437be89e317b79f916bfee0293921b40a6a6323202247	10dcab5c-8a72-436d-8cb8-4166af7535ab	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-11 10:13:10.094033+00	2025-09-04 08:45:05.807821+00	2025-09-04 10:13:10.09403+00
1c5277f6-ef0f-457e-88d5-31f196214946	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	76614fee7b9a1a301b254fca7ebe275315a82b1d0b6bf4c9effa47ad7ee9d12a	2a43534c-b5d7-49cd-8f72-c4a8ebad2875	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-11 10:13:17.972232+00	2025-09-04 10:13:17.972224+00	2025-09-04 10:13:17.972227+00
479b4f19-0529-4157-827c-6b5a55a1f523	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	552f4010f7dcdf3fdf546b581862eab15bcd1c05b02772a79af54e910d21853b	d2766edd-ca5f-4cc9-8724-3bc7d800eb5e	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-11 10:22:10.282018+00	2025-09-04 10:22:10.282003+00	2025-09-04 10:22:10.282006+00
09632d31-739e-4c3c-a7ea-041ceef50467	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	24c01c4a43e600bd522bba9f877aeb32c092ffc9da8e5aa7dd900b7c621a1f59	02a993c5-524e-431b-9a63-5b5f9aedb144	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.66.0.243	2025-09-11 12:15:49.472806+00	2025-09-04 12:15:49.472792+00	2025-09-04 12:15:49.472794+00
9cae4e0b-82de-4ad3-8dd0-d316b63e4919	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	ea5e51cf28fc9b61bdf019e024e4f524b823a24256e22b337fdacc268ff7c564	97d94299-3494-4954-ba86-b90d23f5242e	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.217.31.170	2025-09-11 12:34:58.615306+00	2025-09-04 12:34:58.615298+00	2025-09-04 12:34:58.615301+00
c3a51ed6-1ade-49ac-a54a-719f0f04f315	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	d8aaa4b271f366d8bc52b4118b4a21873da50e31ba3aa2b8ed79677cd2cf633c	31507f3b-48ec-4445-8ef6-15e10dd24bdc	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.217.31.170	2025-09-11 12:36:02.101877+00	2025-09-04 12:36:02.101864+00	2025-09-04 12:36:02.101866+00
3d490384-7106-41a6-9246-488e87f22667	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	ac1e7dd64019b478255e4d1a5ce655cd8629217ba3f9b31efc38abefe97e3dbb	3288e653-2b4c-4266-9d2c-6a3a9d5aac1c	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.217.31.170	2025-09-11 12:36:58.698277+00	2025-09-04 12:36:58.698271+00	2025-09-04 12:36:58.698273+00
6cffc234-6922-4d65-bb41-2b8eede7545e	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	e6d8a53789fa2a62ea2611ec737867ead2689c8dead0559346cf9069ea6df693	517995df-bf96-40bc-bd62-6c34a5eafbae	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-14 23:05:02.038284+00	2025-09-07 00:41:14.792645+00	2025-09-07 23:05:02.038281+00
05a2d488-106e-470a-be72-e5bce8786e0c	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	5ec5efc6a4eef0eda91f2ddb8844bfa6eb287d4297a5df7297b7adbcfbb58876	3204f2cd-c108-43a3-825f-1d82d558d3ea	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-14 23:05:12.65938+00	2025-09-07 23:05:12.65937+00	2025-09-07 23:05:12.659374+00
e784c694-f580-48cb-876c-abfc0ab490b9	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	e46df08c78e03216b8b363cb08494b1fe19d7e819a0875f5c9f4a86623639455	3072b7b7-1c68-4a24-a514-a887e3f19ef9	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-15 00:58:52.401716+00	2025-09-08 00:58:52.401644+00	2025-09-08 00:58:52.401708+00
8e216555-1061-40a9-8e03-1271a93d40ac	be880496-578b-4c2c-aca7-813a09ade3fa	1d5cb09d6dabefa1d6d2d3afe912ee1a97cfc4f8d104592319f96cb0e86153f2	d734044e-f074-44c6-affd-e0e96438f49f	active	testclient	Unknown	2025-09-13 03:21:43.877203+00	2025-09-06 03:21:43.877183+00	2025-09-06 03:21:43.877186+00
8a10d0b6-4180-49a0-ae30-5f76a28b55a3	d108fb7e-144a-4422-89f0-b7242e43df5a	939d83c743ca96d04950fc6e1f63ff9946388441df838f90044b3152b2b4770d	e9650314-efc5-4f66-8325-2e6eb9962281	active	testclient	Unknown	2025-09-13 03:21:54.7684+00	2025-09-06 03:21:54.768381+00	2025-09-06 03:21:54.768384+00
3c555943-682d-47b2-84ae-4530544658ff	2c145dfc-c068-4ac2-9dcb-42050d40cde3	1550627483bd682e9a8f0273a4cdef9a79b4d460774f6bcee58172a178381fa2	7469f26b-96a2-421a-aa13-3ebd1c2f3aff	active	testclient	Unknown	2025-09-13 03:22:00.84089+00	2025-09-06 03:22:00.840873+00	2025-09-06 03:22:00.840875+00
f880ceba-5a6e-4b7b-b11d-5b8352445812	c2c3278d-8c76-468c-a68b-11baf28db541	ddd4d69941b7c70de760d3f1fdf0d7989e96558f6819e138cea25e8c0a339493	28ee3f67-feba-4198-bc88-1fba448665b8	active	testclient	Unknown	2025-09-13 03:29:22.020426+00	2025-09-06 03:29:22.020408+00	2025-09-06 03:29:22.020411+00
c3cacc67-a6ea-4f93-95e1-7e525737df8d	7fc634ed-c4a8-4dab-950f-6a8eb0c5dd05	59b6c1d73b879e2f7b89c0ca44134f62b5fd46d9e907c1fba447b2c61e8e997b	4c0697d6-fc6d-4da1-9dab-03f907079f30	active	testclient	Unknown	2025-09-13 03:31:11.504612+00	2025-09-06 03:31:11.504592+00	2025-09-06 03:31:11.504595+00
ddf9daba-1c16-4053-979e-718abb136bb9	e5ad3259-4c98-4390-a62c-dcb025d21e18	deaec15eb67ac5d693df3e2e25dc59fd130a71bb674ebac52cd9152fda6f2d97	87313b35-c435-43f9-b897-df550f602466	active	testclient	Unknown	2025-09-13 05:06:15.428045+00	2025-09-06 05:06:15.428022+00	2025-09-06 05:06:15.428024+00
aafe98f3-5542-4b40-b72b-71c82b76a5d8	c86ba43e-fc2f-44a4-b08e-a09c4db5c604	1a37e2161a987d9be7a5295cdf9128cba689c95f0659139832406ddb074cf715	fd2bb32b-680a-4bf3-b463-01da59f26d34	active	testclient	Unknown	2025-09-13 05:06:15.807954+00	2025-09-06 05:06:15.807945+00	2025-09-06 05:06:15.807946+00
03285c09-be3c-4947-be9f-8d78e677ea60	953d86f9-d4ec-4970-ba5d-69e40806e531	3a940491191bc0c4e31ae22d1b3f90cc2ec223eb017252318ae1f4b6d40e9378	e0a7d101-9143-405a-8ca4-55ee13aa1500	active	testclient	Unknown	2025-09-13 05:06:16.176122+00	2025-09-06 05:06:16.176112+00	2025-09-06 05:06:16.176114+00
8f5c4c48-cad1-4d51-91c7-829a50610c2f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	ccaf833e8ed409d09924c45dd93dce683d3007025ca1235027aca2b3f30741fb	f52a4938-38d0-456a-aa9b-314e708555bd	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-15 05:15:13.666546+00	2025-09-08 05:15:13.666495+00	2025-09-08 05:15:13.666539+00
e60bceb9-72a5-4be9-8959-812ea347b408	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	122da486adaa8fabfa19237533a363489e52a01fcb02922fe155f9882f500db7	3c598546-2c7c-4fb9-95f9-356a95541e30	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-15 05:15:18.662375+00	2025-09-08 05:15:18.662335+00	2025-09-08 05:15:18.662371+00
8c675f0d-7a51-4dd1-ad04-9133cf7ebc9c	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	6b770852281f4c2d5c5d73dc6c86bc70dcfdf551b695e43b2ebd94e35ec820d3	a6b6a2ad-38a1-498a-87eb-394dcb822651	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	172.217.31.131	2025-09-15 07:20:30.46019+00	2025-09-08 07:20:30.460145+00	2025-09-08 07:20:30.460184+00
0f049f8a-054f-4fb4-8da5-b3bdd5c5bc4f	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	9e9e91c8eb012fc9c9a38def938faca396682a95a5d97fe6617f0ef5f8e4acaa	648a18fd-0c8f-4b59-b933-4ad1698c9660	active	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-15 13:03:07.686759+00	2025-09-08 13:03:07.686699+00	2025-09-08 13:03:07.68675+00
5ce3106b-c938-4e48-a439-1d1166a97f5c	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	8860a1c6448e83dd61b0082c8cdff5f482d6696634ef621d906831ea4d50049b	cfcc187f-dc1e-47ea-b1d7-5861596afb8a	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	172.217.31.131	2025-09-15 07:20:48.61344+00	2025-09-08 07:20:48.613401+00	2025-09-08 07:20:48.613436+00
02a21b35-e361-41a7-a3ec-6fff68cd074e	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	286499c56ff0a568794148262688221a8c24dd791445cbd175c87b4fb5a57a2c	b5cdcc5d-789d-4085-a8b5-f59177dbe749	active	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	172.217.175.67	2025-09-15 13:36:37.68348+00	2025-09-08 13:36:37.683417+00	2025-09-08 13:36:37.683473+00
6611340f-043a-4214-85a7-f79fa1e8b02e	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	ed7f826f11eaaceee354b56b9df5caa407c4797ec06ef07f01cacbd4836db35e	fccda3cb-db16-47eb-9a53-ee8183cbd7ab	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	192.168.65.1	2025-09-15 13:03:01.061225+00	2025-09-08 13:03:01.061153+00	2025-09-08 13:03:01.061219+00
0cda8d65-efee-4507-9654-ef7af6699132	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	00a4ed226835569dbf6312d561474209d778e8e109edbee99daa96a97c82a8f1	098cafdb-84dd-4df5-a9b1-60de753c1343	active	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36	172.217.175.67	2025-09-15 13:36:42.776772+00	2025-09-08 13:36:42.776721+00	2025-09-08 13:36:42.776766+00
1436e32f-cd48-4b34-8459-95426cc7831f	700e3bbf-fda5-4dd0-99ba-0131e70231f1	78fd81d672fc37736512a1366795185630dc3e5921265e9e61abacedb171f84d	39c0079a-61fb-440d-abf5-7383a3f8fc1c	active	testclient	Unknown	2025-09-14 06:19:16.560245+00	2025-09-07 06:19:16.560229+00	2025-09-07 06:19:16.560231+00
96a047be-0ddd-4a10-a1ff-e1fe2f720c0d	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	27ea563bccbea83e086671fa238fa8e4a2e24a9f6efaf79be7e818197875baf2	4323a3eb-c000-4196-8643-4628106a2a19	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	172.217.31.170	2025-09-13 02:19:09.876712+00	2025-09-04 12:38:43.568961+00	2025-09-06 02:19:09.876708+00
492a4ff6-1b7d-4fce-bdb9-8e17d3d23ce4	2ca9086b-f2ae-4018-9ab0-3324ce1b391d	3a46e9bf4f073d5e970d56bfa1c4662676ad5189c385118769d60e9be2a336d5	d6dc9ce6-d966-4a2d-97d8-ae75e0461cc9	revoked	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36	142.250.204.74	2025-09-14 00:41:12.380017+00	2025-09-06 02:34:14.317902+00	2025-09-07 00:41:12.379996+00
\.


--
-- TOC entry 3555 (class 0 OID 16487)
-- Dependencies: 222
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.schema_migrations (version, applied_at) FROM stdin;
001_initial_schema	2025-08-30 10:13:08.584875+00
002_add_password_security_columns	2025-08-30 13:25:41.749427+00
\.


--
-- TOC entry 3550 (class 0 OID 16396)
-- Dependencies: 217
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, email, password_hash, first_name, last_name, role, is_active, email_verified, created_at, updated_at, last_login_at, password_changed_at, failed_login_attempts, locked_until) FROM stdin;
8955190d-e058-43ce-8260-fe5481dbb6e9	test_5406ab4e@example.com	$2b$12$K/3MZ/emgB1h8IjHldBYYuxxZlQcQjn2oeN8iGt5fdCWcv5wo2wMq	Test	User	consultant	t	f	2025-09-01 03:48:49.186574+00	2025-09-03 03:20:53.957561+00	2025-09-03 03:20:54.170844+00	2025-09-01 03:48:49.184375+00	0	\N
b4500643-2d0a-4ebf-92bc-97573468b8fd	test_977530c4@example.com	$2b$12$kKFFSm5r3RbWMuoK6bD6N.3d32Krp8gD5C0KigOw8NQYSRNIeP4PS	Test	User	consultant	t	f	2025-09-01 03:48:54.808949+00	2025-09-01 03:48:54.808951+00	\N	2025-09-01 03:48:54.806632+00	0	\N
b235a250-b4ed-4e3d-b8ed-bc41db64352e	admin_0573de74@example.com	$2b$12$YZ.gsBmFggccSGIxYmYrW.Bd8H.eIm824PMvD9XZTzCrpatB.n0wS	Admin	User	admin	t	f	2025-09-01 03:48:54.984863+00	2025-09-01 03:48:54.984864+00	\N	2025-09-01 03:48:54.983249+00	0	\N
cb240470-da6e-4af9-a163-ac9f277bc06a	test_c6d141bd@example.com	$2b$12$kYjCdT63GGXcDYoe5tqjFeUZumh/i4CyEsAtmhJOFHkCOVZugpxeq	Test	User	consultant	t	f	2025-09-01 03:49:33.702748+00	2025-09-01 03:49:33.70275+00	\N	2025-09-01 03:49:33.70032+00	0	\N
6aa5d05b-3d4c-47ba-a060-84e91d4d506b	test_85da86b9@example.com	$2b$12$U5x4iWTj7lytnxHsF3KdxelMzm46DO.DJThlOqobhHlg4iXVM.oNu	Test	User	consultant	t	f	2025-09-01 03:49:45.985476+00	2025-09-01 03:49:45.985477+00	\N	2025-09-01 03:49:45.982959+00	0	\N
ef5367d3-687c-48d4-a8e7-b40ed394ea23	admin_9ae945b5@example.com	$2b$12$e5o04Sq2gPTy2Y5.SsebJ.tdBpRqSbKRP7DoJg7jXnoE7EFRf.n1u	Admin	User	admin	t	f	2025-09-01 03:49:46.161711+00	2025-09-01 03:49:46.161711+00	\N	2025-09-01 03:49:46.160153+00	0	\N
10ba6ce6-c1bc-4bba-bfb0-a255941172c7	test_bf412a70@example.com	$2b$12$iMgeW.uxe2ZaHawsL023hufXpwGWlJ32dum5XfrvI00jH8q9eLyZ.	Test	User	consultant	t	f	2025-09-01 03:49:46.333961+00	2025-09-01 03:49:46.333961+00	\N	2025-09-01 03:49:46.332663+00	0	\N
4053c638-306e-464c-ae15-c540fe0727fe	other-user-3bb7d20d@example.com	$2b$12$xACZ0eY6Av5yDr2GNcVDl.QEgAug6pkrU1rXhjb.bJgvnyu6yb27K	Other	User	consultant	t	f	2025-08-30 16:04:16.163222+00	2025-08-30 16:04:16.350057+00	2025-08-30 16:04:16.518609+00	2025-08-30 16:04:16.16308+00	0	\N
20eaec0b-8d49-44b4-9ea9-7f79bae4c93c	test_362529b6@example.com	$2b$12$un5IkR/Lnvx0.qtIgDa89.zsbY3HmH2GBfck1s3ZoOrCsPuYZYBNq	Test	User	consultant	t	f	2025-09-01 03:49:46.506125+00	2025-09-01 03:49:46.506126+00	\N	2025-09-01 03:49:46.50467+00	0	\N
50d75441-862f-40ce-bfa6-576137920832	test_8729a7e6@example.com	$2b$12$y2AkLkjW3MbDyNJxq3hV2ed1gGeMZd1c5CbsDV77lDCIIor77mL5u	Test	User	consultant	t	f	2025-09-06 03:14:40.220658+00	2025-09-06 03:14:40.220662+00	\N	2025-09-06 03:14:40.213371+00	0	\N
ef882d6e-b8a5-4357-ab12-25036693b345	test_0fd433af@example.com	$2b$12$yAjLym0sfjd3jdR7yplm5uwfMCP/vRoApX35HfRnZcUn4fIXkCf.6	Test	User	consultant	t	f	2025-09-01 03:49:46.847625+00	2025-09-01 03:49:46.847625+00	\N	2025-09-01 03:49:46.846058+00	0	\N
a617c65b-2789-42a8-a13c-ca3f159ab18e	other-user-82dfaf4a@example.com	$2b$12$HIiS0RG3w5DcYA8aYMY5vuOX2cT6QkoxPsyKfu6ePuenOE9oHvELO	Other	User	consultant	t	f	2025-08-30 15:55:49.208231+00	2025-08-30 15:55:49.208232+00	\N	2025-08-30 15:55:49.208086+00	0	\N
6de36100-c742-4ba5-a6dc-9831cbfddae0	test-nonexistent-aec7ef42@example.com	$2b$12$kuKE9q.avpU7JRWG3Tjx5uHhx7gL57sCcsiGoeyZTVKeAUZOmFww2	Test	User	consultant	t	f	2025-08-30 15:55:49.395591+00	2025-08-30 15:55:49.395593+00	\N	2025-08-30 15:55:49.395411+00	0	\N
f89fa6c5-797e-4230-8244-d02d6d59989d	test_c70361ea@example.com	$2b$12$2eDDFDkUx41FUTEGwrjyuOZT69xFDwA8wWTtuebCkJ/DSy5Y43TX6	Test	User	consultant	t	f	2025-09-01 03:49:47.351493+00	2025-09-01 03:49:47.355147+00	\N	2025-09-01 03:49:47.52212+00	0	\N
7454041c-81bd-4e55-9a54-cecbc52074a1	valid@example.com	$2b$12$v6m11tOZX0f94nu9N37HNu6HlGTDR.iMfbpMj4ZLsB6Rq6b.8ZhY.	Test	User	consultant	t	f	2025-08-30 23:06:13.087752+00	2025-08-31 02:55:06.510259+00	\N	2025-08-30 23:06:13.086216+00	1	\N
1c6bcc85-492d-47b9-ab9a-bd569d8a454a	test_7b2e584c@example.com	$2b$12$b4CPvUFjbO0tJamQv1cxfeY/emno1Ocj/Zlhdu7GaRpV.UkfcRuky	Test	User	consultant	t	f	2025-09-01 03:48:28.057148+00	2025-09-01 22:59:34.867576+00	\N	2025-09-01 03:48:28.054823+00	1	\N
f7986b46-a377-4690-8964-57ebe63d054c	useradmin@example.com	$2b$12$FyN0DbrhN6Vz51U9By.vUee6VEjGNqbFNFmcvqNIEug.9.9Sd80Pe	Test	User	admin	t	f	2025-08-30 23:06:13.423462+00	2025-08-31 02:56:16.558424+00	\N	2025-08-30 23:06:13.422006+00	2	\N
69ff646c-9512-4723-ae84-3391022b6a95	admin@airesumereview.com	$2b$12$135LqrzkuK8YWeM8nOfpYOHCiFhP32ilSV2q3DyOxjlo1TBe8kcQe	Admin	User	admin	t	f	2025-08-31 02:27:12.767143+00	2025-08-31 03:30:04.985536+00	2025-08-31 03:30:05.201877+00	2025-08-31 02:27:12.766565+00	0	\N
e87823d0-ea87-49a5-ab5d-6de30debbc92	test_f4a76b8f@example.com	$2b$12$KPZpJOcREmyMOuSDzeZrE.KjFRP3cacpZaUY8kGdaZPz314HD8eKG	Test	User	consultant	t	f	2025-09-01 03:49:48.030628+00	2025-09-01 03:49:48.717393+00	\N	2025-09-01 03:49:48.029138+00	5	2025-09-01 04:19:48.884463+00
115c12e4-0b08-4f89-bcbf-0bf743985ad6	other-user-8be52686@example.com	$2b$12$SHhPplM7u96VG8VgDfvMLOkJv/B82m2WdtmyzIBsieST.77N2OBVe	Other	User	consultant	t	f	2025-08-30 23:05:44.616195+00	2025-08-30 23:05:44.800717+00	2025-08-30 23:05:44.966719+00	2025-08-30 23:05:44.6161+00	0	\N
27bbcfa7-e5dc-4b4c-83a3-7b826b20d74e	test_257bd911@example.com	$2b$12$hES1VIJs.Yj9QNic4tHN4OFtMwT54KzskNQ6d9.sttnupb6ebRnSW	Test	User	consultant	t	f	2025-09-01 03:49:49.058719+00	2025-09-01 03:49:49.062671+00	\N	2025-09-01 03:49:49.057138+00	5	2025-09-01 03:48:49.062246+00
793ae12a-e2d3-46e6-8691-03dacaa6703f	userconsultant@example.com	$2b$12$vauv3tsVHKILH2M3yMg61ekU9fQmzTqch.j1itDM1v1erdqT5tGHy	Test	User	consultant	t	f	2025-08-30 23:06:13.423457+00	2025-08-30 23:06:13.423458+00	\N	2025-08-30 23:06:13.256413+00	0	\N
24508a5d-ea73-4a01-8d16-bd3204693863	test_b5a32dde@example.com	$2b$12$KQ8zFkmtPh7btzEYk/c0Lep1K6qt7cTCUZFFO1RGYMDK86CBTM63u	Test	User	consultant	t	f	2025-09-01 03:49:49.235978+00	2025-09-01 03:49:49.241684+00	\N	2025-09-01 03:49:49.234627+00	0	\N
ada1d76b-db53-4048-a672-4021a7bae026	other-user-af99978a@example.com	$2b$12$cYoPSxzrdVECKtxixOXVmOzkTihCsm9PgNa6loDstdknVilt.pv1W	Other	User	consultant	t	f	2025-08-30 15:56:46.179184+00	2025-08-30 15:56:46.179185+00	\N	2025-08-30 15:56:46.179063+00	0	\N
0be4a367-8938-4afb-b6e1-28a3d9623d49	test-nonexistent-0065296b@example.com	$2b$12$OWQ/LsOmTwmLCG3WiFicTueLmJLBQlvhwRz9Pi4gaIL.od3lNvfHO	Test	User	consultant	t	f	2025-08-30 15:56:46.366631+00	2025-08-30 15:56:46.366633+00	\N	2025-08-30 15:56:46.366452+00	0	\N
874aeac7-bba5-479d-902a-8a03c64b32c6	test_8f0803b8@example.com	$2b$12$.qT8/XgsDHMeXJBKeK/cYOzM8MCnVNQAbQPJuRiwTll.7uq5TIKzO	Test	User	consultant	t	f	2025-09-01 03:49:49.411931+00	2025-09-01 03:49:49.418995+00	2025-09-01 03:49:49.585588+00	2025-09-01 03:49:49.410342+00	0	\N
18699277-2a74-4bc8-8078-8cf63aa2d173	test_df2c96a9@example.com	$2b$12$xr7Dgub95HP0cLLlBB25pe7ttLJOqu9MpctCCQQQERkb7jwahRhrS	Test	User	consultant	t	f	2025-09-01 03:49:49.759608+00	2025-09-01 03:49:49.759609+00	\N	2025-09-01 03:49:49.758404+00	0	\N
b1556c64-b809-4075-b6c9-acef004a9a37	consultant_6c5efb00@example.com	$2b$12$oE391ltp.4ryAKW.C18Vl.t2tD9mysrDErZsmP.Rwk6BkwKZf49Va	Con	Sultant	consultant	t	f	2025-09-01 03:49:50.097222+00	2025-09-01 03:49:50.097223+00	\N	2025-09-01 03:49:49.930189+00	0	\N
3c80c559-e9d0-41a0-b729-ad10e352ac31	admin_b6cd1d56@example.com	$2b$12$ALIYeLVz1KDCl8LKXm2xL.pSzBuYVzSJM0IXIfVBymPNgFQ3SA1U2	Ad	Min	admin	t	f	2025-09-01 03:49:50.097225+00	2025-09-01 03:49:50.097225+00	\N	2025-09-01 03:49:50.095509+00	0	\N
7d9c8dbf-0772-4027-9832-fa3f706d2b77	test_33b4869c@example.com	$2b$12$bfb9FtbkjAjlCHM.m9YGEOKWfuwSQp6HUCGhGqjRFT7L/dx2o6pVu	Test	User	consultant	t	f	2025-09-01 03:49:50.270949+00	2025-09-01 03:49:50.27095+00	\N	2025-09-01 03:49:50.269993+00	0	\N
417c8f85-c315-4050-85fc-21b998a89c56	test_9c2613ef@example.com	$2b$12$e2ZffAyB7YrNzlQaOd4HD.wdzO8asUiTlNyRqeBQFRW8WYxKpUtB6	Test	User	consultant	t	f	2025-09-01 03:49:50.442909+00	2025-09-01 03:49:50.44291+00	\N	2025-09-01 03:49:50.441514+00	0	\N
d4f8481e-58ae-41a7-b6c3-319ef2d02ec3	test_47fa8d2f@example.com	$2b$12$WBwjvBtQUBA0dKtZoTIHF.PetQcK2VyZGmXS3/rye4QhsoT4EaGYy	Test	User	consultant	t	f	2025-09-01 03:49:50.615389+00	2025-09-01 03:49:50.61539+00	\N	2025-09-01 03:49:50.61392+00	0	\N
077feb22-9287-4e19-aea9-ff806e48a917	valid_bc909331@example.com	$2b$12$VFDNQE5MCx6UCGfpEe0LluX5LilKqMzJAt5fdWqC6AjQsLfnak75C	Test	User	consultant	t	f	2025-09-01 03:49:50.787464+00	2025-09-01 03:49:50.787465+00	\N	2025-09-01 03:49:50.786423+00	0	\N
338bdbe7-d456-4076-8295-1df859b3b141	test_user_c9eef817@example.com	$2b$12$BjesAPsv4Oa./hezj/RZE.R7bLnqZEkROALFuHZfjO7ybl9oP4nLq	Test	User	consultant	t	f	2025-09-01 03:49:51.298566+00	2025-09-01 03:49:51.298566+00	\N	2025-09-01 03:49:51.297273+00	0	\N
39523eb9-409e-4824-84cd-227bd386a331	test_a7fbc261@example.com	$2b$12$SwjTXpLBqYDHi7Fo89vjwe.0dgSKfYxdbSs55rofB7k7P/hwPSBfe	Test	User	consultant	t	f	2025-09-01 03:52:04.224261+00	2025-09-01 03:52:04.231198+00	\N	2025-09-01 03:52:04.399055+00	0	\N
edea9ad1-65f1-434a-9838-9dd86a998912	other-user-5c746b71@example.com	$2b$12$htQM9TadDUkrWusrbD0uKe3K0FB5vbpqPBPSUX6t7sKj/h3JEh31e	Other	User	consultant	t	f	2025-08-30 15:59:17.405512+00	2025-08-30 15:59:17.592593+00	2025-08-30 15:59:17.760763+00	2025-08-30 15:59:17.405363+00	0	\N
54170246-52e1-4c2a-adf5-832938e2aee3	test_01d4d4a8@example.com	$2b$12$9Y7V6Xgb6vzWta6fVwJBoOTkn7QNORVQLhm3unJtGvQ2e2nhRwUFm	Test	User	consultant	t	f	2025-09-01 03:52:05.708992+00	2025-09-01 03:52:06.484848+00	\N	2025-09-01 03:52:05.707059+00	5	2025-09-01 04:22:06.660797+00
40e469b0-3141-46c8-b6eb-db6518a3158e	other-user-c04216e6@example.com	$2b$12$prxuTXfpnbA0Ci2OrMHWb.We6F4EJV010JD/fDfBgNBMABu5t9aJq	Other	User	consultant	t	f	2025-08-30 23:05:07.595613+00	2025-08-30 23:05:07.777177+00	2025-08-30 23:05:07.943549+00	2025-08-30 23:05:07.595524+00	0	\N
e919e130-e383-45dc-8baf-40dc7e58939c	test_b9d66f69@example.com	$2b$12$4brPhqEpNoEX78zoQ.2rju0hSeu5RWWt19ClWljFw54XHEsva8Yva	Test	User	consultant	t	f	2025-09-01 03:52:07.630183+00	2025-09-01 03:52:07.641119+00	2025-09-01 03:52:07.813774+00	2025-09-01 03:52:07.628155+00	0	\N
263ed478-aa63-4fe0-acdd-cc56592aed31	test_74d181ff@example.com	$2b$12$yfwt8vuOEMOGGzA6/0Xee.Odhntw2ZeEJbbtViu9V2K0G1rM9vuG2	Test	User	consultant	t	f	2025-09-01 04:02:51.160421+00	2025-09-01 04:02:51.855481+00	\N	2025-09-01 04:02:51.158102+00	5	2025-09-01 04:32:52.023222+00
2e61e51a-917c-4a21-83d3-abbe4dadf6ae	test_1997ea9f@example.com	$2b$12$T6b75hsfScxpSpZcLPdLzOKoeUgYeaNg1vdIL5pR1aNjfwL1Muv0W	Test	User	consultant	t	f	2025-09-01 04:02:52.196584+00	2025-09-01 04:02:52.202554+00	2025-09-01 04:02:52.373692+00	2025-09-01 04:02:52.195097+00	0	\N
76fa9c2d-288e-4da4-a19c-23cf334c1d77	test_ccb1c07e@example.com	$2b$12$SR5C6eeUiSa1I3I/HLm6buyEDE01ZaK0rOIAECyeYHb900t29Ucu6	Test	User	consultant	t	f	2025-09-01 04:03:05.399185+00	2025-09-01 04:03:05.399187+00	\N	2025-09-01 04:03:05.396508+00	0	\N
cd509a31-45b3-4663-91a2-b033774157d2	admin_1f47c113@example.com	$2b$12$WwlsxAyclAoiPW6Dxrv2z.5S3L6rBph9m098vsa/B0tHjoRqW29Y6	Admin	User	admin	t	f	2025-09-01 04:03:05.575025+00	2025-09-01 04:03:05.575026+00	\N	2025-09-01 04:03:05.57357+00	0	\N
f1ad6e7e-75f3-457c-b0b5-50d0c309b972	test_601f9894@example.com	$2b$12$fRUWQoM.itDf4ZMIgKvWX.yUaami2AaFMFh1TM3HE66pJnfgAyQuK	Test	User	consultant	t	f	2025-09-01 04:03:05.74948+00	2025-09-01 04:03:05.749481+00	\N	2025-09-01 04:03:05.748096+00	0	\N
4ec69322-e16b-49e3-a19a-eec01d3658c8	test_1b9c1ff8@example.com	$2b$12$2IM7C6FuNTNfM/pIh0XUoe.1IhlQHnkRmLO75C6l0XFXd1yJMfUWS	Test	User	consultant	t	f	2025-09-01 04:03:05.922353+00	2025-09-01 04:03:05.922354+00	\N	2025-09-01 04:03:05.921008+00	0	\N
f373420a-27a8-4d0c-842a-1331a83dd0b4	test_735018db@example.com	$2b$12$TSbXbKXI6oXCK/5S.4DLyuQklr0bpjAMJCDkXWVShsfvRisIvo/HC	Test	User	consultant	t	f	2025-09-01 04:03:06.265175+00	2025-09-01 04:03:06.265176+00	\N	2025-09-01 04:03:06.263354+00	0	\N
5f4ec9a1-f223-4bef-90d1-6553dae72001	test_36cc7ffa@example.com	$2b$12$VusvlNqltT.CwMyphPiKvO0hFma/u88JG9VzgEC3v15Oq4zPbiUdu	Test	User	consultant	t	f	2025-09-01 04:03:06.771848+00	2025-09-01 04:03:06.774826+00	\N	2025-09-01 04:03:06.94183+00	0	\N
af265bd9-55dd-4d27-8399-51acc573c3fa	test_da70749e@example.com	$2b$12$VtSLUmA3/5DVCOFHy4RjaugBKAlz7ApWm5vGb.YmC0bYkjHGrE2rm	Test	User	consultant	t	f	2025-09-01 04:03:07.454974+00	2025-09-01 04:03:08.140377+00	\N	2025-09-01 04:03:07.453321+00	5	2025-09-01 04:33:08.307833+00
d0ccc7cf-e2a9-4906-b4be-7a7c9853f8c1	test_b00f8468@example.com	$2b$12$5bvXrY24fAtENBBflK/7q.EAQ8l3o..L.aBJyvh5NrjXeP0b4yRnO	Test	User	consultant	t	f	2025-09-01 04:03:08.479719+00	2025-09-01 04:03:08.483428+00	\N	2025-09-01 04:03:08.478186+00	5	2025-09-01 04:02:08.483113+00
44b9e02a-b4e2-4974-9313-552d8f952e01	test_1bb4407f@example.com	$2b$12$Nx4jF5qtsFzajxlpi9MzAulEQ2w2q248iYamTmqUKM0rxOnlYcWXe	Test	User	consultant	t	f	2025-09-01 04:03:08.654409+00	2025-09-01 04:03:08.660476+00	\N	2025-09-01 04:03:08.653041+00	0	\N
9663287a-d5b5-490b-a70b-009f16d03839	test_17531ab3@example.com	$2b$12$R.wodlXWiJVa3sy7Odea/.pbZw96Q3iJR8zTG/cBi4bIOMHsgH1mm	Test	User	consultant	t	f	2025-09-01 04:03:08.83281+00	2025-09-01 04:03:08.838637+00	2025-09-01 04:03:09.007044+00	2025-09-01 04:03:08.831628+00	0	\N
5287d6e0-6082-48c4-8556-8110b32b6439	test_c31660e7@example.com	$2b$12$LRQoEB7/HcAzNO8BmwxCNu8q7daEoMSNyfWbRDuHU.ZUZ3zF8tg8y	Test	User	consultant	t	f	2025-09-01 04:03:09.180355+00	2025-09-01 04:03:09.180355+00	\N	2025-09-01 04:03:09.179087+00	0	\N
117cc6df-2ae4-4f42-94bf-e4f65a4d1d9b	consultant_1da86200@example.com	$2b$12$L7hGakf31hBlTaOhWqeDWu3aY0YzyQ.Kyr0z/5wFBTaG8dZTfA466	Con	Sultant	consultant	t	f	2025-09-01 04:03:09.524498+00	2025-09-01 04:03:09.524499+00	\N	2025-09-01 04:03:09.353879+00	0	\N
b44cd1a3-873b-4506-88b4-fa91912ff7f4	admin_f716a8cf@example.com	$2b$12$VJAMSkCqsE8.CGSYKf/9PO/khEGHcVEbo5MkVK9QrZt1YvK4r//yi	Ad	Min	admin	t	f	2025-09-01 04:03:09.524502+00	2025-09-01 04:03:09.524502+00	\N	2025-09-01 04:03:09.522501+00	0	\N
7d6dc8ae-221a-4bd4-bf46-37a61fe29f44	test_73a5d792@example.com	$2b$12$LDQaRgIrkh3Y2BkxKn4Miux6yRmsk12/tNxikyOMLxUcBfV5qzjSm	Test	User	consultant	t	f	2025-09-01 04:03:09.699577+00	2025-09-01 04:03:09.699579+00	\N	2025-09-01 04:03:09.698255+00	0	\N
956c97c6-c1f6-40aa-93f2-07644b967604	test_cb44fced@example.com	$2b$12$HtVLLC1UyzTRXBsBYgrRF.tHG6ViNhOdlrohhq4cmAvxvlUPiudPS	Test	User	consultant	t	f	2025-09-01 04:03:09.873392+00	2025-09-01 04:03:09.873393+00	\N	2025-09-01 04:03:09.871709+00	0	\N
4cb37c2f-f12d-4132-9962-4bf64178319e	test_a25d6a55@example.com	$2b$12$qDl0jczOY2m06WVM1LocwebepbaTGe0KASLb/PcoSOztdYIFne/ey	Test	User	consultant	t	f	2025-09-01 04:03:10.045015+00	2025-09-01 04:03:10.045016+00	\N	2025-09-01 04:03:10.043779+00	0	\N
0319d244-86d1-4332-820e-d2c8143918d6	valid_66bd9931@example.com	$2b$12$ZhrZnnV2zRSeZ82otnrEv.X.nA/J4vAGhqvU4/8En2ZcnFJvfL6Hi	Test	User	consultant	t	f	2025-09-01 04:03:10.2166+00	2025-09-01 04:03:10.216601+00	\N	2025-09-01 04:03:10.215057+00	0	\N
1c37091f-05b7-4fa6-a76b-3811e8123c59	test_user_625088c9@example.com	$2b$12$JhmpglqLCB.sFCdplq9qUu6BbXCm5a43kDIpZhOh8KnwjjQYPeGbG	Test	User	consultant	t	f	2025-09-01 04:03:10.727709+00	2025-09-01 04:03:10.727711+00	\N	2025-09-01 04:03:10.726268+00	0	\N
5db6e714-c446-4291-a8cf-5c0cd50a217b	test_3557c7d6@example.com	$2b$12$31tvOa4kZ/LXbDI6YKnR3e9X3iRxpFCVTgnSIPjuwRTd4UqqRRiz2	Test	User	consultant	t	f	2025-09-01 04:08:08.991179+00	2025-09-01 04:08:08.998801+00	\N	2025-09-01 04:08:09.167043+00	0	\N
0c751b7d-0392-4abd-8fba-410fe165b17f	test_815b2b94@example.com	$2b$12$c3.Lup18b5N/I4bS1i2Kbuw5eRusSd3roJ2Efk12QIRXsxLe04xSe	Test	User	consultant	t	f	2025-09-01 07:34:41.454838+00	2025-09-01 07:34:41.458892+00	\N	2025-09-01 07:34:41.626512+00	0	\N
e30288e3-52be-4b31-8804-bc25a69f5640	user_consultant_ea13ca66@example.com	$2b$12$hp/yBtWpbJwmgecu7p7sr.e/zu85DwxxTRRo9jpC4AWHjS3lY2hUi	Test	User	consultant	t	f	2025-09-01 07:34:42.487147+00	2025-09-01 07:34:42.487149+00	\N	2025-09-01 07:34:42.30916+00	0	\N
bc4e7865-faa2-43ae-899d-2e8200738f9c	user_admin_c621385f@example.com	$2b$12$R2fH2nteR2B2SfK1ypmFJOtPi9BCqdVrBON.wEKYc1EDuAfCWYuyi	Test	User	admin	t	f	2025-09-01 07:34:42.487151+00	2025-09-01 07:34:42.487152+00	\N	2025-09-01 07:34:42.486315+00	0	\N
2fa01716-7ed4-453d-b450-deb5ea7b5855	test_0efd13e8@example.com	$2b$12$i1UPB.enz/wY1eNq6p/RZ.doI0neHD5XsVsT2bST.FT6f4PwKm3o.	Test	User	consultant	t	f	2025-09-01 07:35:01.173924+00	2025-09-01 07:35:01.173926+00	\N	2025-09-01 07:35:01.171559+00	0	\N
ae7c9669-16d7-45d9-93fb-d5009659eaed	admin_01598c0f@example.com	$2b$12$yEkPuj3412ga1p8G/xWyCOaq1jS6CiBDe7ewjN52/C8eacrJnapaO	Admin	User	admin	t	f	2025-09-01 07:35:01.35096+00	2025-09-01 07:35:01.350961+00	\N	2025-09-01 07:35:01.349328+00	0	\N
83b53169-560f-402b-87ac-8d128bcdb14e	test_95e038e1@example.com	$2b$12$RFD4ATYyWPepsYNLiGiZ2.sq8d3uh5YXyXKWYRzhnEBHTwhhYjxNG	Test	User	consultant	t	f	2025-09-01 07:35:01.527369+00	2025-09-01 07:35:01.527371+00	\N	2025-09-01 07:35:01.526764+00	0	\N
3f765014-a48a-4066-a827-21c28db52cb4	test_cc466edc@example.com	$2b$12$HAY/t5RdsB9fj/pAu7aI9eqLbkdRt0RH4fYXDPZ31H7lSpFSJg7QC	Test	User	consultant	t	f	2025-09-01 07:35:01.697505+00	2025-09-01 07:35:01.697506+00	\N	2025-09-01 07:35:01.695932+00	0	\N
9bc2644f-8c16-42d9-ad2d-ccb6819f22df	test_3ac1deb8@example.com	$2b$12$/LBqnkcXQzSizvWlTWL9y.qX5nZuvkZK1fcVabKZZ4TmHEzPue7ya	Test	User	consultant	t	f	2025-09-01 07:35:02.03922+00	2025-09-01 07:35:02.039222+00	\N	2025-09-01 07:35:02.037467+00	0	\N
1740a570-dc12-43fe-bc7b-3146ea87cf6a	test_d0256c53@example.com	$2b$12$NikAnlTeEEr4P84mAASzyuYr2IxzUDZoDXitmxSkKFDwfuE50jY0W	Test	User	consultant	t	f	2025-09-01 07:35:02.543042+00	2025-09-01 07:35:02.546223+00	\N	2025-09-01 07:35:02.713186+00	0	\N
91146707-a380-4e5b-8645-9e92362a2b89	test_9df98ca7@example.com	$2b$12$FiVrbnGxM4EXLN54xTGp.OSofQVQGTNPfPZ9V2x77BqXG4yfIqqEO	Test	User	consultant	t	f	2025-09-01 07:35:03.387057+00	2025-09-01 07:35:04.074458+00	\N	2025-09-01 07:35:03.385414+00	5	2025-09-01 08:05:04.241287+00
b03d45f5-90bc-4b35-9122-1caae3a0f63d	test_77cf3b1f@example.com	$2b$12$Ik7gL2BmUjdCbIJ1rQQUeO9Ty0StkC.cbxkDMVKHwLn2Rr0QUzJay	Test	User	consultant	t	f	2025-09-01 07:35:04.413973+00	2025-09-01 07:35:04.417986+00	\N	2025-09-01 07:35:04.412325+00	5	2025-09-01 07:34:04.417504+00
871c2d2e-aabc-4437-887a-47d91a093be1	test_842f0581@example.com	$2b$12$ymoUVVt6wELohl2.rhEztOu7XW5TY/68V1Mnlhc0aoRXijo.rRp6q	Test	User	consultant	t	f	2025-09-01 07:35:04.590218+00	2025-09-01 07:35:04.596919+00	\N	2025-09-01 07:35:04.588713+00	0	\N
c2338e33-8b16-4f07-9555-94774d66d869	test_c998a92b@example.com	$2b$12$K03PYBtxw5ku/gW6f4d9G.evY0w3pTYi9LjL3n0s24p0f93vMh8b6	Test	User	consultant	t	f	2025-09-01 07:35:04.768041+00	2025-09-01 07:35:04.773252+00	2025-09-01 07:35:04.94071+00	2025-09-01 07:35:04.766902+00	0	\N
822bfde6-242d-4a74-9215-95228ed49a6c	test_4adc83da@example.com	$2b$12$7VwjvSGn.ZYEbEiEpaLSuui2/j17kKe1pAJ.zof4/9Vb0JwToIBQS	Test	User	consultant	t	f	2025-09-01 07:35:05.116089+00	2025-09-01 07:35:05.11609+00	\N	2025-09-01 07:35:05.114438+00	0	\N
bf14cf06-51e4-4717-97db-3224c7bcb1ab	consultant_ac725c5f@example.com	$2b$12$jsBWV7.8xD6TAQmkXGy8b.frfz12o8pJQdP0xr8ZhBxZcvxGq3VGO	Con	Sultant	consultant	t	f	2025-09-01 07:35:05.454323+00	2025-09-01 07:35:05.454324+00	\N	2025-09-01 07:35:05.287315+00	0	\N
cfec0e4c-f474-4935-be7c-7ff58c7a175f	admin_2fd8445f@example.com	$2b$12$4VJDMLWA917zs46wVx9U1ukqGOYHVnoV6I7mAbnGHdbq5ulWQ49ca	Ad	Min	admin	t	f	2025-09-01 07:35:05.454327+00	2025-09-01 07:35:05.454327+00	\N	2025-09-01 07:35:05.453018+00	0	\N
6a191948-3bf7-4924-86be-dde12ce9f2ab	test_93c00d5c@example.com	$2b$12$d.6H5KMlwio2jw4VD1tQdecl8Ag998eZlUZl0YM9VAo8nsh95yjlC	Test	User	consultant	t	f	2025-09-01 07:35:05.628443+00	2025-09-01 07:35:05.628445+00	\N	2025-09-01 07:35:05.626836+00	0	\N
d1982d92-c564-43d0-9ab5-51f93408f619	test_45e27599@example.com	$2b$12$knzeMCj0FhjbS7UzN2tfF.eFt/a1tyQSX6n59ExiHJ687cUU0NN9q	Test	User	consultant	t	f	2025-09-01 07:35:05.803985+00	2025-09-01 07:35:05.803986+00	\N	2025-09-01 07:35:05.802544+00	0	\N
41a6b7fe-178b-4c49-9ebb-93a69d15164f	test_1841d2e5@example.com	$2b$12$Ih0twYZIXBOHm8tnT0Xwqe2nm4fJIzgT6CtW5.x121IJy0qAi2Pe.	Test	User	consultant	t	f	2025-09-01 07:35:05.9768+00	2025-09-01 07:35:05.976801+00	\N	2025-09-01 07:35:05.975186+00	0	\N
12401015-a049-42e4-8927-1859ac956744	valid_27d41b3b@example.com	$2b$12$1mEhc.nvGFG1DNAqwrrvLOwehbK4ucqojJhMv5sPBA4Ay35ZfkG0e	Test	User	consultant	t	f	2025-09-01 07:35:06.149717+00	2025-09-01 07:35:06.149717+00	\N	2025-09-01 07:35:06.148256+00	0	\N
15c6fb26-6ee9-4954-9289-7e1d04d306d4	user_consultant_92d0b911@example.com	$2b$12$mZ/uy9rRnOu1FRBw0Fx/u.NDYqqG8fpUC0fnX8v/3GponKvmqu3S.	Test	User	consultant	t	f	2025-09-01 07:35:06.48684+00	2025-09-01 07:35:06.486841+00	\N	2025-09-01 07:35:06.319834+00	0	\N
f9531845-2e7a-4118-8005-12f05c1de86f	user_admin_39d2c1fb@example.com	$2b$12$F2olGlmg6NnOXbBAU/KVwO7QSXvYnsbWxecC3WeS7pcRe1bweYHsO	Test	User	admin	t	f	2025-09-01 07:35:06.486844+00	2025-09-01 07:35:06.486844+00	\N	2025-09-01 07:35:06.485317+00	0	\N
d2d88e6c-44a5-4f25-ac56-45b259651bac	test_user_2587631e@example.com	$2b$12$t1Oam5lAjLC62A67Qu48susCUqPRvyZ6WY6Ma9WKy1oVk0/v4MMou	Test	User	consultant	t	f	2025-09-01 07:35:06.82852+00	2025-09-01 07:35:06.828521+00	\N	2025-09-01 07:35:06.826897+00	0	\N
41bd5dca-5838-464c-958d-4683a81fec74	test_66127211@example.com	$2b$12$ym4U8ZiiC6TpmDkkyhDSBui9DgF2ilkP4Z84tX.kq9UXEJG1blqCW	Test	User	consultant	t	f	2025-09-01 08:09:03.34285+00	2025-09-01 08:09:03.342852+00	\N	2025-09-01 08:09:03.340628+00	0	\N
597c83c3-a091-452c-918f-fb0ae9c2a1cb	admin_792bd77e@example.com	$2b$12$co9gSQ5tMiLc14RwoHPgK.gidiyFxD4aIgjwAXs.t8nnfJNX7JT.a	Admin	User	admin	t	f	2025-09-01 08:09:03.520533+00	2025-09-01 08:09:03.520534+00	\N	2025-09-01 08:09:03.519111+00	0	\N
6e53d91a-e2ee-465a-bf3a-57752902333b	test_48c6393c@example.com	$2b$12$vEJdhAkkXEjG6.wbVOmwpuLACAmdxSgQpS/aJOt.jp.r6o0wvPBni	Test	User	consultant	t	f	2025-09-01 08:09:03.98942+00	2025-09-01 08:09:03.989421+00	\N	2025-09-01 08:09:03.987476+00	0	\N
fea4932c-7e17-4fee-a674-bf15b257f97a	test_0123f709@example.com	$2b$12$YkA6Xk5KQ9Fk2RZ1hvjIWeeXJv58ku/jveJBWZN/lyavT2JWOkysK	Test	User	consultant	t	f	2025-09-01 08:09:04.32871+00	2025-09-01 08:09:04.328711+00	\N	2025-09-01 08:09:04.327144+00	0	\N
c0df88ab-7ccb-4337-8cfd-06f61635cb04	test_44d1f20b@example.com	$2b$12$dweweArixT2cOlO31OIbhuTV17PsHA0TXw947mWmZJR7oOSrmm/jW	Test	User	consultant	t	f	2025-09-01 08:09:04.840244+00	2025-09-01 08:09:04.841743+00	\N	2025-09-01 08:09:05.008742+00	0	\N
b5f72736-0af2-4601-9d89-803452f6cff1	test_9abb60df@example.com	$2b$12$KNx8GoaVcpkaOjPfRs5eQe1ohiCIf/tMtmrhdkvvNkumalotNFPN6	Test	User	consultant	t	f	2025-09-01 08:16:40.943933+00	2025-09-01 08:16:40.943941+00	\N	2025-09-01 08:16:40.941387+00	0	\N
28a16e07-030a-4a31-ae53-137b01a8933a	admin_ca0836c0@example.com	$2b$12$KtD6CkqCJGWs6CM.sIQvPeboRUm4lMfvBALJSaY39uo4xvefbAC.y	Admin	User	admin	t	f	2025-09-01 08:16:41.132403+00	2025-09-01 08:16:41.132405+00	\N	2025-09-01 08:16:41.131146+00	0	\N
5c81562d-e7db-4c66-a589-510cf60205f3	test_b097e8b3@example.com	$2b$12$WkzDPvJOTsOcu3U7WlszaOrzIYz9Br76PreEttmfpfsJVSf6PJcJW	Test	User	consultant	t	f	2025-09-01 08:16:41.313816+00	2025-09-01 08:16:41.313817+00	\N	2025-09-01 08:16:41.312096+00	0	\N
2587ec2a-6eda-4c0d-9f71-8a0f51808d0b	test_aa95c83e@example.com	$2b$12$fMqQ6G278J8adba910v61ePF6rvkaq1PaCyTUeoyn3w8E5cQHyQiS	Test	User	consultant	t	f	2025-09-01 08:16:41.491101+00	2025-09-01 08:16:41.491102+00	\N	2025-09-01 08:16:41.490054+00	0	\N
e2294905-9945-400b-97f0-1cba660228cc	test_7d09b641@example.com	$2b$12$SBDQrnsuaE2yF.tO5ZgST.ndJhusunzBgIHoT/oWY1YvK3fz19BTy	Test	User	consultant	t	f	2025-09-01 08:09:05.522431+00	2025-09-01 08:09:06.20959+00	\N	2025-09-01 08:09:05.521371+00	5	2025-09-01 08:39:06.376318+00
d871b8f5-ae46-4854-89c3-709cef1888c2	test_54e3c604@example.com	$2b$12$tHyK5Qj3Ufnr66jDSx.0de1i.PlBoqEbgdFSjPiTFtzAHMV2MNUiu	Test	User	consultant	t	f	2025-09-01 08:09:06.55361+00	2025-09-01 08:09:06.557855+00	\N	2025-09-01 08:09:06.551912+00	5	2025-09-01 08:08:06.557175+00
66018d19-f04b-4bc0-93a2-3fa21dbff979	test_a5075cf4@example.com	$2b$12$YF1IYdsfEc1pCImBOw.s9ubi5bVVGLqxrVtSXlgilbNRaHoEw7xjm	Test	User	consultant	t	f	2025-09-01 08:16:41.837729+00	2025-09-01 08:16:41.837731+00	\N	2025-09-01 08:16:41.836282+00	0	\N
99a3957f-9823-43d5-9e98-6235fbe5ff73	test_595dc605@example.com	$2b$12$Zdb/BScU9.yAv9wQOgR0GOHLJqbA0iBLIvZ7IknRjHS6j4ZsMaOsi	Test	User	consultant	t	f	2025-09-01 08:09:06.730089+00	2025-09-01 08:09:06.739374+00	\N	2025-09-01 08:09:06.728286+00	0	\N
79ac4d8a-54e8-44b3-bc45-a95d13561e1e	test_3ab4833d@example.com	$2b$12$ecnho/C6FogA70LG.mUTA.VL8fM.QsCXW6CxlIlLwk9F8uoTZVVjO	Test	User	consultant	t	f	2025-09-01 08:16:42.362493+00	2025-09-01 08:16:42.363655+00	\N	2025-09-01 08:16:42.542103+00	0	\N
1c3a046a-1a3f-4f5c-9a10-4911f6d33293	test_c0b3baeb@example.com	$2b$12$apW0TUhHWfJh4oIQ09LK0uFVL4CkGgd9Q8hOO2om./7GPE7wt4P0y	Test	User	consultant	t	f	2025-09-01 08:09:06.912781+00	2025-09-01 08:09:06.919775+00	2025-09-01 08:09:07.087554+00	2025-09-01 08:09:06.911322+00	0	\N
56355753-748b-47a1-92a5-7594bcf4eec7	test_836b0591@example.com	$2b$12$hojczzmN8/e8TcyCgrTcBesTNT5/MR23vfDLSsdG1SAAXpkOobugO	Test	User	consultant	t	f	2025-09-01 08:09:07.265561+00	2025-09-01 08:09:07.265562+00	\N	2025-09-01 08:09:07.263725+00	0	\N
9bec2465-252c-420d-b85f-d00c2fd72171	test_98dad5be@example.com	$2b$12$YX4gHnw1NKrVaEjLslceiOm.aig5fdJzrSzgX7SQNzVlvkYasA3l.	Test	User	consultant	t	f	2025-09-01 08:09:07.892957+00	2025-09-01 08:09:07.892957+00	\N	2025-09-01 08:09:07.891312+00	0	\N
abfce608-5e68-4410-97ae-3f102d5aa3e4	test_6e68119f@example.com	$2b$12$fUYlGuZen9/LEQMGfN4sl.bOygOD0rnIbhx03yJIKtPphf7ydoxXa	Test	User	consultant	t	f	2025-09-01 08:09:08.066437+00	2025-09-01 08:09:08.066438+00	\N	2025-09-01 08:09:08.064889+00	0	\N
39ad112f-c613-4b33-a7f3-bd253e41dc42	test_dd997778@example.com	$2b$12$ujkJQzktrz6i6ShHdKmrbux5NyI.LWM9kcxtMNWuy5HIp6fZSN0fq	Test	User	consultant	t	f	2025-09-01 08:09:08.239697+00	2025-09-01 08:09:08.239698+00	\N	2025-09-01 08:09:08.238112+00	0	\N
5b39733b-c010-49ab-8fbb-264353db6407	test_user_b3f9fe4f@example.com	$2b$12$c/pkwD65ToGgbMRWiqpdrOZWMSluFGn13IEa5eQbZVmEqSXmqqTOq	Test	User	consultant	t	f	2025-09-01 08:09:09.154844+00	2025-09-01 08:09:09.154845+00	\N	2025-09-01 08:09:09.153364+00	0	\N
977af479-fcb5-4734-9bf1-2c8f42b52f6d	test_e2909ec9@example.com	$2b$12$AxoagnusKFajFIMB2YkFcucdrvesbWcFExaZmzPaUcK3B6pV3H47i	Test	User	consultant	t	f	2025-09-01 08:16:43.243125+00	2025-09-01 08:16:43.944278+00	\N	2025-09-01 08:16:43.242244+00	5	2025-09-01 08:46:44.118266+00
2da1d80e-bf75-4d52-957d-69f8fc6070de	test_56a4e22b@example.com	$2b$12$FUOpfJ05UoFCoZ.45xyJqupF82uyEtA3Shcm.gaWNIBg3N0Y7NIw.	Test	User	consultant	t	f	2025-09-01 08:16:44.295144+00	2025-09-01 08:16:44.297453+00	\N	2025-09-01 08:16:44.294311+00	5	2025-09-01 08:15:44.297289+00
200a49a5-595a-48be-b4df-278eb6a970fa	test_e23e2abe@example.com	$2b$12$NHhLyjEVEnH42QA8CArwL.pbOGJ8XUb3zEaqBX.Ag5Ukt3WoeGVCq	Test	User	consultant	t	f	2025-09-01 08:16:44.473235+00	2025-09-01 08:16:44.478766+00	\N	2025-09-01 08:16:44.471981+00	0	\N
2d064a86-4634-49e1-951e-e1b50da73585	test_338ccc88@example.com	$2b$12$LVazqw.NontWRhFMeXD1xOGOTHz0qWkRbvD2kxNW1ZAEEe8KioHwu	Test	User	consultant	t	f	2025-09-01 08:16:44.655782+00	2025-09-01 08:16:44.662452+00	2025-09-01 08:16:44.834361+00	2025-09-01 08:16:44.654532+00	0	\N
6f44f824-c8fc-4959-8e36-46ce83fa2742	test_924c1c9b@example.com	$2b$12$L/GSeusCotYigO76L.ls2ebQJgWPHPZpaJbE2hZTs8GukOnYM9n56	Test	User	consultant	t	f	2025-09-01 08:16:45.017684+00	2025-09-01 08:16:45.017686+00	\N	2025-09-01 08:16:45.016959+00	0	\N
21912b38-7d8b-495f-af68-5ac1bba161d8	consultant_6ee127d0@example.com	$2b$12$TjNSW/cTu5EJKePX.JDP2.zpcfIVThEy6MKNgXjMDc3d4i0b9EsZq	Con	Sultant	consultant	t	f	2025-09-01 08:16:45.365694+00	2025-09-01 08:16:45.365696+00	\N	2025-09-01 08:16:45.19193+00	0	\N
e65f5bf2-c478-4907-808f-c769ddfee8c8	admin_a5cc8207@example.com	$2b$12$vWbMHpSQ1K3D.XU4L3M41.Twlpz/LXc/fwUbUaSbV5ILKKqxcQhum	Ad	Min	admin	t	f	2025-09-01 08:16:45.365698+00	2025-09-01 08:16:45.365699+00	\N	2025-09-01 08:16:45.364637+00	0	\N
f51ec4ee-6d6f-44bf-aefb-9e44d3773c7b	test_a647453e@example.com	$2b$12$i9A8Dn5sV4p5OBiMuB4tKOYRwZw1OI60U53X4QugkSRbT/sPy2xnC	Test	User	consultant	t	f	2025-09-01 08:16:45.542342+00	2025-09-01 08:16:45.542344+00	\N	2025-09-01 08:16:45.54099+00	0	\N
6e081a26-6fa5-46bf-b200-a5f96e902661	test_e0a66b62@example.com	$2b$12$Inmg55ZboYTlEVKCnaESYe/aBJZRA44f996721DscVm.NvKoXW9Ne	Test	User	consultant	t	f	2025-09-01 08:16:45.72154+00	2025-09-01 08:16:45.721542+00	\N	2025-09-01 08:16:45.720284+00	0	\N
1516ccef-062e-42d2-bfe4-1ec48297bf03	test_e54c4981@example.com	$2b$12$AT74GpQXoGB32vQgw0RNqu0TXiuIm5xDeYHpiGg80u24d2xQxG3Ne	Test	User	consultant	t	f	2025-09-01 08:16:45.898207+00	2025-09-01 08:16:45.898208+00	\N	2025-09-01 08:16:45.897388+00	0	\N
11055d3b-4103-4de1-942c-07224bf360de	valid_ecadd21e@example.com	$2b$12$rv00mXwTxqKe5N6j0QrVPeoVYqQD6rld.l1.Z89KpdvTy5BtXfAFC	Test	User	consultant	t	f	2025-09-01 08:16:46.079244+00	2025-09-01 08:16:46.079246+00	\N	2025-09-01 08:16:46.078157+00	0	\N
e4c9336f-0017-46a7-bac2-62b6d4bd7003	user_consultant_eebfeb02@example.com	$2b$12$RYMinPIrnIgTMxaaJBKNqO76SLNp0YCOg.eYwb1D4Uk6mA6WLbN/2	Test	User	consultant	t	f	2025-09-01 08:16:46.423931+00	2025-09-01 08:16:46.423932+00	\N	2025-09-01 08:16:46.253814+00	0	\N
71e22730-4854-4b50-a0d9-558d0f1b6f78	user_admin_bf187b01@example.com	$2b$12$B6CEjYAo6OnZlF.quQNyGOJ4HS4VDK0AS39JqoZzHqXaE8BsdeTP6	Test	User	admin	t	f	2025-09-01 08:16:46.423935+00	2025-09-01 08:16:46.423935+00	\N	2025-09-01 08:16:46.42283+00	0	\N
fb5f6037-0e86-483c-b08b-99d599531582	test_user_87b35497@example.com	$2b$12$hqKkBG.k4roM71hMsGjAi.sO5ajja8yJeRFXXdsZm/SpuQ8Nysfxq	Test	User	consultant	t	f	2025-09-01 08:16:46.773873+00	2025-09-01 08:16:46.773875+00	\N	2025-09-01 08:16:46.772208+00	0	\N
aaea7597-e20c-49de-9aea-74cd8715fab6	test_193ae3b4@example.com	$2b$12$u4ITjwGDFSL79OH3l/U0huwQBiO3VnIrzC3p7VI0KD4lYZmaXhBlC	Test	User	consultant	t	f	2025-09-01 08:20:58.274071+00	2025-09-01 08:20:58.274073+00	\N	2025-09-01 08:20:58.271559+00	0	\N
33768374-8153-4252-abef-6810ef0f6aaf	admin_d038fae8@example.com	$2b$12$zXS/TB6tw24eKsXP8UaLLOqknV.NPUpe3GprPPW1oYPC.VPljXJ7C	Admin	User	admin	t	f	2025-09-01 08:20:58.462543+00	2025-09-01 08:20:58.462545+00	\N	2025-09-01 08:20:58.461564+00	0	\N
51484d9d-1bdd-4a33-8971-82a3aa3a1b9a	test_545b6bca@example.com	$2b$12$ffhWl3iqjaOgQJKmrbBHz.gGPpPIqvVwIu7aOVJ41.gpK.t45QQ46	Test	User	consultant	t	f	2025-09-01 08:20:58.649199+00	2025-09-01 08:20:58.649201+00	\N	2025-09-01 08:20:58.648125+00	0	\N
ad7fa6c2-68a9-4777-b5a1-b380b2a53890	test_130e6e35@example.com	$2b$12$itnvF4ZfwIDwiCUDEeIf1O0qc824a4/sSKVWv0.deSDhuv1/tELte	Test	User	consultant	t	f	2025-09-01 08:20:58.837227+00	2025-09-01 08:20:58.837228+00	\N	2025-09-01 08:20:58.836281+00	0	\N
729e66b8-ec61-4c61-9a86-20800da5adcf	test_41be95e0@example.com	$2b$12$n3M4ar7leDhPv8O520TGkO6AyzmutWyGa11/L5dlI0YB4r526tN4m	Test	User	consultant	t	f	2025-09-01 08:20:59.211612+00	2025-09-01 08:20:59.211615+00	\N	2025-09-01 08:20:59.21036+00	0	\N
7a62e928-8917-46c1-a2d0-f0f5eea92b40	test_22a2b052@example.com	$2b$12$f/7945qh1Vs6uvRhN/54G.DupaZLH3JEakdYAwzEr7XMrDa3JjnW6	Test	User	consultant	t	f	2025-09-01 08:20:59.809378+00	2025-09-01 08:20:59.811832+00	\N	2025-09-01 08:20:59.993157+00	0	\N
66fcc2cb-0c8e-4573-9889-c8cc88c2d798	test_45193cda@example.com	$2b$12$PobaEj1Gud8hhc59yA6I..C5t0Il0otXhxO8Pmrxhle4KF7Rc3yWO	Test	User	consultant	t	f	2025-09-01 08:21:00.724283+00	2025-09-01 08:21:01.455896+00	\N	2025-09-01 08:21:00.723036+00	5	2025-09-01 08:51:01.634456+00
c0ec1c48-2880-46e0-9733-b5a694a34d6a	test_54865d7f@example.com	$2b$12$GAQ8X70Vsb.yFsQuQadGWOxBH/SHkSeGxVY8tq5PlwR3E0SmTY/2K	Test	User	consultant	t	f	2025-09-01 08:21:01.818714+00	2025-09-01 08:21:01.820766+00	\N	2025-09-01 08:21:01.817505+00	5	2025-09-01 08:20:01.82099+00
aab0a6c5-213d-464e-aaed-dbbc62e4d471	test_f2826b33@example.com	$2b$12$9UpNRb3A6Hsfd8UIGIDIEOJU1FPAH3XqdDneTc9V6xFnxcZtWnPIK	Test	User	consultant	t	f	2025-09-01 08:21:02.004746+00	2025-09-01 08:21:02.009214+00	\N	2025-09-01 08:21:02.003906+00	0	\N
0783bbc8-c19d-4ed4-8fca-0cd0c569b6e1	test_11f2325c@example.com	$2b$12$svhHFJ5dKTVhcN8IfMYrQujQlRkjwgG.6621T4p7v2Q5Q1bCHRSCe	Test	User	consultant	t	f	2025-09-01 08:21:02.191168+00	2025-09-01 08:21:02.196803+00	2025-09-01 08:21:02.375127+00	2025-09-01 08:21:02.190122+00	0	\N
517f66ac-12e3-484b-90d0-1fa8cadf3809	test_9bfd31a9@example.com	$2b$12$MJAKhBjg6TBPhY5btEzybOTGFXAvfa4dtkYKlx9i1LoBMvMRkIh2u	Test	User	consultant	t	f	2025-09-01 08:21:02.567033+00	2025-09-01 08:21:02.567034+00	\N	2025-09-01 08:21:02.566318+00	0	\N
3b9ddfc9-832e-4a4e-9fea-ee3d81a1fa98	consultant_056aa638@example.com	$2b$12$y7at4SeQwd/h5QKMEtihbOwMPWVoweFoM1RA9uYXn3yUc7.KfhnPy	Con	Sultant	consultant	t	f	2025-09-01 08:21:02.925059+00	2025-09-01 08:21:02.92506+00	\N	2025-09-01 08:21:02.747382+00	0	\N
f392a8bf-07e9-4cb4-a0ea-68a8a571fa6f	admin_b0b1b569@example.com	$2b$12$Wrainy0YFElkhB.TJBiLtOgh7yWlLPBxrlnFH0DZH0y09cJbjnlD.	Ad	Min	admin	t	f	2025-09-01 08:21:02.925063+00	2025-09-01 08:21:02.925063+00	\N	2025-09-01 08:21:02.923717+00	0	\N
efde1214-0e18-4efe-b985-c8ddee57c840	test_e88849c7@example.com	$2b$12$G04y1er/fxEFi53WeGXEtuClJiaLGMFWzfvT4yr2W.wyeQN8h6M1S	Test	User	consultant	t	f	2025-09-01 08:21:03.108785+00	2025-09-01 08:21:03.108786+00	\N	2025-09-01 08:21:03.107205+00	0	\N
522a406a-a6ca-4f26-8227-b0f771185021	test_ff570924@example.com	$2b$12$R0f9M82Tc1g2hqNDdTv0oOA0FQicxxaX6iaAs6InMuimwZ.Cnw.Su	Test	User	consultant	t	f	2025-09-01 08:21:03.294095+00	2025-09-01 08:21:03.294098+00	\N	2025-09-01 08:21:03.292654+00	0	\N
8fe143f1-70c3-40d5-ad80-8d197747cdcb	test_5063357d@example.com	$2b$12$qki.RXix774hg/npP3rif./s4adHFpI.nsx625RgVVo/ucQlcZre.	Test	User	consultant	t	f	2025-09-01 08:21:03.477478+00	2025-09-01 08:21:03.477479+00	\N	2025-09-01 08:21:03.476232+00	0	\N
40e3b86f-b81e-4103-9efe-bb9c36465ff6	valid_662f934d@example.com	$2b$12$dAK4I6fF0h/v/O/eV2DDDeWQT/AbFzyIv/YLX56MYky0rDV/QQey6	Test	User	consultant	t	f	2025-09-01 08:21:03.657864+00	2025-09-01 08:21:03.657865+00	\N	2025-09-01 08:21:03.656611+00	0	\N
fe630148-69f1-44d1-94e2-1954e302b9e0	user_consultant_ce39120e@example.com	$2b$12$ojd/TDDta3U4dyxTiM3W1.S.fg7JlnC2vghyEVA3PtXckVkDEWp/2	Test	User	consultant	t	f	2025-09-01 08:21:04.021967+00	2025-09-01 08:21:04.021968+00	\N	2025-09-01 08:21:03.843696+00	0	\N
d6137e9b-32af-4eb1-89aa-a8a65c553506	user_admin_d4da8ebd@example.com	$2b$12$hRjpLH01Rx3xcEDiSQO3CeQ3wAFOpgTXrp4rkjMg9sWOdblK8CCx6	Test	User	admin	t	f	2025-09-01 08:21:04.021972+00	2025-09-01 08:21:04.021973+00	\N	2025-09-01 08:21:04.020327+00	0	\N
72f88e8a-5bda-4c1b-86b7-29a9b9b3465f	test_user_a3cc3f16@example.com	$2b$12$783c7YxE8g4qz9NPOjmWZ.GAR9gY1EBXWZmy8Mz6fLxUd7Hryz752	Test	User	consultant	t	f	2025-09-01 08:21:04.386011+00	2025-09-01 08:21:04.386012+00	\N	2025-09-01 08:21:04.385045+00	0	\N
66af5fa0-e05c-410d-8fa4-d7928cfd9494	test_8fb63318@example.com	$2b$12$siNsi.QTW8IVKptEpHw7ceWt/Z0RyQwIeU1.HDU12E4uA0Fb3aRiG	Test	User	consultant	t	f	2025-09-01 08:34:51.551631+00	2025-09-01 08:34:51.551633+00	\N	2025-09-01 08:34:51.549571+00	0	\N
da4f973b-6b85-497e-bed3-271fddbd49ff	admin_08b708fd@example.com	$2b$12$wY7nxDhnINdrKY19.Aox6eggMTB0HiewWZuzE3QXzdTyyCSdxfaHa	Admin	User	admin	t	f	2025-09-01 08:34:51.736337+00	2025-09-01 08:34:51.736339+00	\N	2025-09-01 08:34:51.73523+00	0	\N
d8317f07-28ca-492e-93a9-02328c0949a9	test_de2732c5@example.com	$2b$12$FZiROW1/JivAYlKeJOqjauNiUx8kzWCyVyq1aZQKFgVkXUCV4269O	Test	User	consultant	t	f	2025-09-01 08:34:51.927933+00	2025-09-01 08:34:51.927935+00	\N	2025-09-01 08:34:51.926197+00	0	\N
37e75bb1-97c2-4810-b4f9-3b365899cc77	test_10d1a5df@example.com	$2b$12$ScsMQjlG8SHGMxXGQZeSn./KRSJPnjEgDEmanV/GQRtowUSZjdlvS	Test	User	consultant	t	f	2025-09-01 08:34:52.108509+00	2025-09-01 08:34:52.108511+00	\N	2025-09-01 08:34:52.107259+00	0	\N
a21dc682-e6c6-42b1-92c5-2273b9fcb988	test_d91b5b86@example.com	$2b$12$agwKqYIHwi.Dz6xLHGujTu8nQUfzexuzGEECf2au0qO/wqWXSogea	Test	User	consultant	t	f	2025-09-01 08:34:52.463755+00	2025-09-01 08:34:52.463757+00	\N	2025-09-01 08:34:52.462558+00	0	\N
3a69bd68-5c88-4bd4-bef4-af307e77aaf2	test_96189d61@example.com	$2b$12$6Wv.H7sVniF8Ctsl7J.cN.Qy2kqc9zpXoOHuxF9VRIWNDorEHZm.G	Test	User	consultant	t	f	2025-09-01 08:34:53.00435+00	2025-09-01 08:34:53.008139+00	\N	2025-09-01 08:34:53.192568+00	0	\N
a81514c8-c2da-46ed-9af4-3395d594f214	test_cf93820b@example.com	$2b$12$0ohcLZybgngK7ngpf.NLpOyQAO.I48ixufR/PReFKfBvzbpomJExe	Test	User	consultant	t	f	2025-09-01 08:34:53.949975+00	2025-09-01 08:34:54.732782+00	\N	2025-09-01 08:34:53.948752+00	5	2025-09-01 09:04:54.908338+00
594a0c54-d61d-4bf0-af84-b7ace7a91ae5	test_e82b913a@example.com	$2b$12$QVLKFOo5ivMG2qgSP1zdz.5x3icG.SIaeTilKrr/aveGQXx3lzHMa	Test	User	consultant	t	f	2025-09-01 08:34:55.094397+00	2025-09-01 08:34:55.098561+00	\N	2025-09-01 08:34:55.092673+00	5	2025-09-01 08:33:55.098128+00
2f21aa00-a079-47e8-9017-54578e4eebfa	test_f07183e1@example.com	$2b$12$C3K.9oH8TpWaxiI2kQ1SU.JqwJqFOvxnU80hs4qVuLh0DT.p1o61G	Test	User	consultant	t	f	2025-09-01 08:34:55.277488+00	2025-09-01 08:34:55.28273+00	\N	2025-09-01 08:34:55.276678+00	0	\N
73b96386-e3a3-4461-9653-2486a533605b	test_700bf8bd@example.com	$2b$12$ykbQdvJmDKUPApVSLURSSOqJ7cdYDTdbnZjA6zgCOHmgL1xkL7.u2	Test	User	consultant	t	f	2025-09-01 08:34:55.486356+00	2025-09-01 08:34:55.488878+00	2025-09-01 08:34:55.662933+00	2025-09-01 08:34:55.485682+00	0	\N
0f54cf50-0f9b-45aa-8886-ac66647c5982	test_4e3f4b95@example.com	$2b$12$zDKgCbTpw0zk3BZqFVd0l.Kn6REEZziuDfjBk/drDtHHTLf6SVLxW	Test	User	consultant	t	f	2025-09-01 08:34:55.849421+00	2025-09-01 08:34:55.849422+00	\N	2025-09-01 08:34:55.848397+00	0	\N
b29b7981-97ec-4035-a9bb-796e957a3d4d	consultant_e29ca7ab@example.com	$2b$12$WGhbI6EyOpJHg20hFS1S5.Y7xYCCxDWvgfciTvc6u7px0Kv2SkRj.	Con	Sultant	consultant	t	f	2025-09-01 08:34:56.219528+00	2025-09-01 08:34:56.21953+00	\N	2025-09-01 08:34:56.032242+00	0	\N
78357615-8ca5-46c4-98f6-c5e60547238b	admin_0ed82d1a@example.com	$2b$12$H5/gbB04BHqlo.LFt7UDi.20zZkdKjBoI5VAwIWhkkOTt2mWvzMk2	Ad	Min	admin	t	f	2025-09-01 08:34:56.219533+00	2025-09-01 08:34:56.219533+00	\N	2025-09-01 08:34:56.218603+00	0	\N
4ddd3d74-71a5-4ca6-8340-3049b87484b5	test_51ed76a3@example.com	$2b$12$iondXd2PMaQetNpm/8CROeHrGcFlVsRPvlxmV83QvkwRSeo1WhQ8W	Test	User	consultant	t	f	2025-09-01 08:34:56.399153+00	2025-09-01 08:34:56.399156+00	\N	2025-09-01 08:34:56.397081+00	0	\N
0d4e7038-48ef-4524-99d0-78ea77e69ec3	test_742483de@example.com	$2b$12$tHKu3tuOvo/JazuNyxF8A.Mg46YyTjb1JHX951qqV/vkZsXUs/cOa	Test	User	consultant	t	f	2025-09-01 08:34:56.58976+00	2025-09-01 08:34:56.589761+00	\N	2025-09-01 08:34:56.588228+00	0	\N
595ea765-31d4-4d7e-8402-493aefa335e6	test_b9a8009b@example.com	$2b$12$0gtDci2IvFqbN/bUigwTBOuXxcdpqT75tBfGA9UneRFMBnGN3RfTK	Test	User	consultant	t	f	2025-09-01 08:34:56.786251+00	2025-09-01 08:34:56.786253+00	\N	2025-09-01 08:34:56.785414+00	0	\N
05db32bf-e9ef-4dcc-8a7f-b62dcfdfe162	valid_07eddf0b@example.com	$2b$12$AAVa29oFVwCla45Y8g0pNOsrSNr1YOXsKw6za3XMrBxPFX4eHcIHG	Test	User	consultant	t	f	2025-09-01 08:34:56.964716+00	2025-09-01 08:34:56.964717+00	\N	2025-09-01 08:34:56.963325+00	0	\N
a0c56fb5-c97f-4651-88ff-8b4ebce9d112	user_consultant_ef7ce2e1@example.com	$2b$12$vJjY//nCuMeOUc6JG4ORD.8l7xJhKoqMqFbmVL4m3ItMNJdRqpP3O	Test	User	consultant	t	f	2025-09-01 08:34:57.321218+00	2025-09-01 08:34:57.32122+00	\N	2025-09-01 08:34:57.140615+00	0	\N
c9c693c6-0a6d-4552-8a22-e9e622f93496	user_admin_5de9f949@example.com	$2b$12$RhzDKjNvEA2XfQ6J8vyTPeTzP.t1Z56MPkSHsIDP2vyMfDn./O/M2	Test	User	admin	t	f	2025-09-01 08:34:57.321223+00	2025-09-01 08:34:57.321223+00	\N	2025-09-01 08:34:57.320282+00	0	\N
8b9a7a1c-e4af-4ea0-9b71-12c05a2f47f5	test_user_40ddd31a@example.com	$2b$12$ko2CnCGUKs7rwlHjDrLsXu.3EpIu3LvxYnWe/CYRysCwV790eYEqG	Test	User	consultant	t	f	2025-09-01 08:34:57.678294+00	2025-09-01 08:34:57.678296+00	\N	2025-09-01 08:34:57.676412+00	0	\N
a668a677-43b5-4393-90f0-3cb773e85af8	integration.test@example.com	$2b$12$Nb2HblXaHDr7klpe.3vWWep.IA4/48YDSVk01tRUbvsbq.KBDZwgK	Integration	Test	consultant	t	f	2025-09-01 08:40:16.302817+00	2025-09-01 08:40:16.313886+00	2025-09-01 08:40:16.48149+00	2025-09-01 08:40:16.3005+00	0	\N
8eefec12-4b00-4792-9941-0c218f2efd8e	logout.test@example.com	$2b$12$9K8l1rQoL/9pRVWuYx1hG.m8dT8vueZe85j7PAmOYZcW4piqgIhUO	Logout	Test	consultant	t	f	2025-09-01 08:40:26.063137+00	2025-09-01 08:40:26.073917+00	2025-09-01 08:40:26.243764+00	2025-09-01 08:40:26.060815+00	0	\N
fd891ad5-9ac4-45f5-a7c3-54a93cf84338	invalidation.test.020d0fdf@example.com	$2b$12$D.t9WA.jD6O08nKwD1dQp.ylNM72Ut8oV/Uq2cJ9/oqyVYXeF3Tzi	Invalidation	Test	consultant	t	f	2025-09-01 08:40:26.434086+00	2025-09-01 08:40:26.443306+00	2025-09-01 08:40:26.614436+00	2025-09-01 08:40:26.432442+00	0	\N
ad85b2ec-60da-4d83-a361-728584b24e30	multiple.logout.517237a3@example.com	$2b$12$ubvzOb6g2oJV6LUqm6JQ6.fL0BiY0by1ccnYg7c8JrwW/hUUywDSi	Multiple	Logout	consultant	t	f	2025-09-01 08:40:26.805509+00	2025-09-01 08:40:26.814278+00	2025-09-01 08:40:26.980864+00	2025-09-01 08:40:26.803725+00	0	\N
60d41dfa-7ac7-4171-bf4f-58f0683809f0	content.type.a1947d51@example.com	$2b$12$ZMaf/iQjES4cXlf3iYsNT.UgoAidYJABzARR.aJS1rDrLnmY8Qgy6	Content	Type	consultant	t	f	2025-09-01 08:40:27.164709+00	2025-09-01 08:40:27.171086+00	2025-09-01 08:40:27.337123+00	2025-09-01 08:40:27.163659+00	0	\N
79c8d447-4cbd-4b91-927b-22cfa4c9f853	admin_2ea71b53@example.com	$2b$12$qOs328mFApuxt1T5F5MOeuZ1OSV7D3zT6boULEienXL6r5JnMXOee	Admin	User	admin	t	f	2025-09-06 03:14:40.429146+00	2025-09-06 03:14:40.429148+00	\N	2025-09-06 03:14:40.426072+00	0	\N
47739dbc-82dd-4649-833d-de9dc478b5c5	test_9ed94a48@example.com	$2b$12$08xxoK.eYnHBM0cIgs3QwemD1PrUt3yuGCpvcLZwrVAMrStgUsstK	Test	User	consultant	t	f	2025-09-06 03:14:40.61147+00	2025-09-06 03:14:40.611472+00	\N	2025-09-06 03:14:40.609834+00	0	\N
5aa692c1-d1f4-47d0-ae0b-a69c73635f82	test_c0b0ef11@example.com	$2b$12$9D2YqHnMBCY92CYCLZz5XO8mV4rIZK7F6xjc.xCTOuVerji1QilYu	Test	User	consultant	t	f	2025-09-06 03:14:40.788944+00	2025-09-06 03:14:40.788946+00	\N	2025-09-06 03:14:40.787757+00	0	\N
8d6ae0a3-8b47-470a-aae0-968d86449c48	invalidation.test.857250e6@example.com	$2b$12$rGsdSli4Mc4kPMQ65C8xiOjnBZPmE2ahGDktJky4c12zOhDG.Ncyy	Invalidation	Test	consultant	t	f	2025-09-01 08:42:45.246402+00	2025-09-01 08:42:45.258708+00	2025-09-01 08:42:45.429043+00	2025-09-01 08:42:45.244945+00	0	\N
a05f0ecf-04f8-4738-acc5-7011d811abbe	test_7935ee9b@example.com	$2b$12$IxbrN3XLhFtBV0MykqDU3.CjpqYONmK/tYPOnQ22DN9kLRBDkUDn2	Test	User	consultant	t	f	2025-09-06 03:14:41.1375+00	2025-09-06 03:14:41.137501+00	\N	2025-09-06 03:14:41.136263+00	0	\N
ce5313d9-aec9-4270-9084-82f761ea98c4	multiple.logout.a608749a@example.com	$2b$12$FmQK1vb3WJOPeP7rrdsB9ugw5N4z8qQ4ZRH5cc4T51yg2PDJ6fxc6	Multiple	Logout	consultant	t	f	2025-09-01 08:42:45.634527+00	2025-09-01 08:42:45.639818+00	2025-09-01 08:42:45.806713+00	2025-09-01 08:42:45.633674+00	0	\N
79518cb6-a6d1-4795-8c83-089e9e9606d9	content.type.8c85ad4c@example.com	$2b$12$cyfGCNOzLM/lzjP/.oNSh./5LO1/K.YOSCeee16FXqRh4XJWbg9QG	Content	Type	consultant	t	f	2025-09-01 08:42:45.990732+00	2025-09-01 08:42:45.994848+00	2025-09-01 08:42:46.162318+00	2025-09-01 08:42:45.990167+00	0	\N
991705a2-773b-4ed9-9de1-48104d82746b	test_0d4f313b@example.com	$2b$12$qA5CY6k23uSSRXwTjCd5tupyQqLcsn8PqeWpDkGOrSW37156RReiW	Test	User	consultant	t	f	2025-09-06 03:14:41.682039+00	2025-09-06 03:14:41.684117+00	\N	2025-09-06 03:14:41.856729+00	0	\N
8440eac3-c341-4227-852b-7cecdc9ac0da	test_fe5ffcac@example.com	$2b$12$vkfkFXnXiYHI8aSeDEVnee9NgOkV39BUu3CzfpYltkuvovhaHgFXi	Test	User	consultant	t	f	2025-09-06 03:14:42.558477+00	2025-09-06 03:14:43.255889+00	\N	2025-09-06 03:14:42.556833+00	5	2025-09-06 03:44:43.427142+00
087a8528-c781-4ad2-b8b6-7c7c12b5b9f5	test_1993bc34@example.com	$2b$12$pqoLRDAnBhOBbIsAjAIpves2dPeYtj04N3WK3Fg/9URQEeQunL8uO	Test	User	consultant	t	f	2025-09-06 03:14:43.621265+00	2025-09-06 03:14:43.624988+00	\N	2025-09-06 03:14:43.619679+00	5	2025-09-06 03:13:43.624666+00
31c94bbd-4740-4373-b6d3-e0f132cafe70	test_964f5cdc@example.com	$2b$12$mBd9A7oDKvWs8Q62QUKi4.tUL8QEopdczr0XII1k6kQl9WCSd4xqe	Test	User	consultant	t	f	2025-09-06 03:14:43.800355+00	2025-09-06 03:14:43.806775+00	\N	2025-09-06 03:14:43.798966+00	0	\N
cbc0c847-0ea3-41b2-b4be-78bf98c22f03	test_ad862983@example.com	$2b$12$ZNmSOOn6OIGxsKuKvQN12u/4tPVymzvXG/iVToatTo3mWxY.tw/9u	Test	User	consultant	t	f	2025-09-06 03:14:43.98317+00	2025-09-06 03:14:43.988987+00	2025-09-06 03:14:44.158527+00	2025-09-06 03:14:43.981694+00	0	\N
752cfde1-d14e-497e-a8e2-b4ee55a8c96e	test_8c78f097@example.com	$2b$12$LcsnoK09GnCAD2xe9uKtgu2gr6JSR.821imangzmDjLoUftTvQbgS	Test	User	consultant	t	f	2025-09-06 03:14:44.338257+00	2025-09-06 03:14:44.338259+00	\N	2025-09-06 03:14:44.337584+00	0	\N
04add264-42ce-4aad-911d-1e6293b861fa	consultant_5daea64a@example.com	$2b$12$rSAwOUV/fozgdGTWcsdVUuBYLXdQxOrvexMIsX0I1pqnYV3bQ/bOq	Con	Sultant	consultant	t	f	2025-09-06 03:14:44.684254+00	2025-09-06 03:14:44.684256+00	\N	2025-09-06 03:14:44.513778+00	0	\N
d666e65b-589d-44a8-ad9b-be41c7759a3b	admin_8fde58b1@example.com	$2b$12$u0Cx/y8KMXRfAxfcriK85ezGsdvNdWItB/FkC2Q7iUEYffmI0lXta	Ad	Min	admin	t	f	2025-09-06 03:14:44.684259+00	2025-09-06 03:14:44.684259+00	\N	2025-09-06 03:14:44.682545+00	0	\N
4cf72ff8-8e5c-4c2a-88c0-1c9e0c5009df	test_e9671b0e@example.com	$2b$12$0aWlJ/6B4A17Ij/amAQ4Ze9OfmyMYT.sm2F11gQOlzc2W7vbmwrlS	Test	User	consultant	t	f	2025-09-06 03:14:44.861369+00	2025-09-06 03:14:44.86137+00	\N	2025-09-06 03:14:44.859721+00	0	\N
b6ce5529-d6c3-4366-ad45-908af09edbfa	test_0759219b@example.com	$2b$12$kVtEIHavL96BfHLThoiL9ePg7Aqa.gZ3sP7goq94sbFotXbyHNg0e	Test	User	consultant	t	f	2025-09-06 03:14:45.038868+00	2025-09-06 03:14:45.03887+00	\N	2025-09-06 03:14:45.037394+00	0	\N
03a0c8b1-e13b-4972-9dee-b6db148f43cb	test_ce14581e@example.com	$2b$12$cmf/KvjpQ/yBTXp1C/aTK.PIcg09ZqMC0cUmIFix7lo2GFv7lIYq.	Test	User	consultant	t	f	2025-09-06 03:14:45.214061+00	2025-09-06 03:14:45.214063+00	\N	2025-09-06 03:14:45.213123+00	0	\N
fad38520-49cc-4217-96ac-5dc07a289d06	valid_10ad2c74@example.com	$2b$12$tYKyspLVEfU49Q4eQQAFde0BsnGdUacVNm58OBKAdIJIevyfNAuze	Test	User	consultant	t	f	2025-09-06 03:14:45.389092+00	2025-09-06 03:14:45.389093+00	\N	2025-09-06 03:14:45.387672+00	0	\N
a4342d4c-9f6f-4086-ae4f-fe61e8d51b33	user_consultant_5037f1a0@example.com	$2b$12$hprOJvSO1EkulQ.4lVsybeBuYiFVNgtmsRKkJOxviHvh/kzubTclK	Test	User	consultant	t	f	2025-09-06 03:14:45.731765+00	2025-09-06 03:14:45.731768+00	\N	2025-09-06 03:14:45.56234+00	0	\N
0fc3b849-f125-47fb-959f-0d6f3545a828	user_admin_757a3f10@example.com	$2b$12$GMGDS8zHSLEGJfVUy9y2nOfMWZAV3vz94NYQHw4Euj1fYeWJbeDJS	Test	User	admin	t	f	2025-09-06 03:14:45.73177+00	2025-09-06 03:14:45.73177+00	\N	2025-09-06 03:14:45.731068+00	0	\N
695f834d-f6ac-4232-8ecd-c6af92ca93a3	test_user_ca1b6dcd@example.com	$2b$12$8a6gW.zUfypcasIbSFP7ve88GCiWYHgUcA1Aig7.9U4qNwt/5uG7i	Test	User	consultant	t	f	2025-09-06 03:14:46.079674+00	2025-09-06 03:14:46.079675+00	\N	2025-09-06 03:14:46.078096+00	0	\N
be880496-578b-4c2c-aca7-813a09ade3fa	test_user_ecf98b33@example.com	$2b$12$Ov34CQWcrcZByJMgSfKbne6YaR2tc8ZbrsYxJ68tejBvUEh301oFO	Integration	Test	consultant	t	f	2025-09-06 03:21:43.66857+00	2025-09-06 03:21:43.692154+00	2025-09-06 03:21:43.862604+00	2025-09-06 03:21:43.666941+00	0	\N
d108fb7e-144a-4422-89f0-b7242e43df5a	test_user_f85c277b@example.com	$2b$12$URnu0.g7N5ujtXB.kYYm7u3zKAFNhWELrCPJvNR4ZQhj5S.G83w4G	Integration	Test	consultant	t	f	2025-09-06 03:21:54.549157+00	2025-09-06 03:21:54.58123+00	2025-09-06 03:21:54.754539+00	2025-09-06 03:21:54.546814+00	0	\N
2c145dfc-c068-4ac2-9dcb-42050d40cde3	test_user_4bc5bbff@example.com	$2b$12$0e21W3PjC2DWDiql9C88CeoFN.Zekh7N1VjlZ2wnGGaVvfd2/Td0a	Integration	Test	consultant	t	f	2025-09-06 03:22:00.649928+00	2025-09-06 03:22:00.659134+00	2025-09-06 03:22:00.83103+00	2025-09-06 03:22:00.648153+00	0	\N
807d0cae-1e14-4c55-aa7d-0808f7d63cd6	test_user_b1d91ece@example.com	$2b$12$Y7SmlC67wZoTR.e3Gei3r.9U2lu3ihskAhTuKoIITTKLVQx3aVymu	Test	User	consultant	t	f	2025-09-06 03:29:07.954356+00	2025-09-06 03:29:07.954358+00	\N	2025-09-06 03:29:07.951831+00	0	\N
c2c3278d-8c76-468c-a68b-11baf28db541	test_user_de0de499@example.com	$2b$12$cOWeO3t53aSLv9ntASDqHe0MRG2CrVM4G9xgjCncMjnX7MYSWuosS	Integration	Test	consultant	t	f	2025-09-06 03:29:21.83075+00	2025-09-06 03:29:21.83981+00	2025-09-06 03:29:22.011502+00	2025-09-06 03:29:21.828953+00	0	\N
7fc634ed-c4a8-4dab-950f-6a8eb0c5dd05	test_user_1a1ac1dd@example.com	$2b$12$vHwsBqn23Lhrz7n.tA8VkOS16nZY.6jQOvUYPqtU79r9hQYTymDYe	Integration	Test	consultant	t	f	2025-09-06 03:31:11.308579+00	2025-09-06 03:31:11.319445+00	2025-09-06 03:31:11.489983+00	2025-09-06 03:31:11.30683+00	0	\N
e5ad3259-4c98-4390-a62c-dcb025d21e18	invalidation.test.87d42fbd@example.com	$2b$12$sHU.eUfbshBJxYzvvfAvI.fo5szi44PNGfw6dwohD5R54RIkYp87y	Invalidation	Test	consultant	t	f	2025-09-06 05:06:15.222673+00	2025-09-06 05:06:15.240308+00	2025-09-06 05:06:15.415143+00	2025-09-06 05:06:15.221346+00	0	\N
c86ba43e-fc2f-44a4-b08e-a09c4db5c604	multiple.logout.542ed197@example.com	$2b$12$pVs7wJT3RDmA7DkAyIw.lOlGJikuYVRXqV2DwG7Qw0xblVhNLaLOO	Multiple	Logout	consultant	t	f	2025-09-06 05:06:15.628604+00	2025-09-06 05:06:15.633196+00	2025-09-06 05:06:15.803356+00	2025-09-06 05:06:15.627973+00	0	\N
953d86f9-d4ec-4970-ba5d-69e40806e531	content.type.c3f6e890@example.com	$2b$12$JqWj1PV7cTI1sdKRux7/pebwjY1M1PoZ0xlpEdUaocSsSkJwnOrTq	Content	Type	consultant	t	f	2025-09-06 05:06:15.994067+00	2025-09-06 05:06:16.001462+00	2025-09-06 05:06:16.171027+00	2025-09-06 05:06:15.992807+00	0	\N
9c7fcc1b-8cee-4817-b099-33f1562ab566	test@example.com	$2b$12$QYvfa4NmwnsXgnSU/vZmF.B6Ww.qlFRXlgwSSLCvNyXV4eAsLC0P.	Test	User	consultant	t	f	2025-08-30 23:06:08.823516+00	2025-09-07 06:19:16.92967+00	2025-08-31 03:57:53.950358+00	2025-08-30 23:06:08.821295+00	4	\N
d0699f13-e94a-4e5c-be51-b2abcee5991b	test_511b82c0@example.com	$2b$12$7jygvesoDh23Va2t5XNo6eVF1dCwOKZNquZOMosdXN2s.Sxql2kru	Test	User	consultant	t	f	2025-09-06 05:06:58.132247+00	2025-09-06 05:06:58.132249+00	\N	2025-09-06 05:06:58.129841+00	0	\N
083d1560-fd4b-432c-b909-b346549d2c6c	admin_b7857b10@example.com	$2b$12$6mfqXUeaOmzRZAH9IVVe7e/nXnn6wH0KqXG/SuoIxRojvd1ERxwmO	Admin	User	admin	t	f	2025-09-06 05:06:58.311164+00	2025-09-06 05:06:58.311165+00	\N	2025-09-06 05:06:58.309581+00	0	\N
8fa5c440-66bb-4b6d-82ec-eb827d7e0b55	test_55ea4375@example.com	$2b$12$m0u0Mfslsyb6oftcIyFY1.lFNSdZJdD/nlAMofKR.pBo2QJcmbQIW	Test	User	consultant	t	f	2025-09-06 05:06:58.49284+00	2025-09-06 05:06:58.492843+00	\N	2025-09-06 05:06:58.492229+00	0	\N
a5f443ac-f398-43b5-af0b-e97e32c7f2fc	test_8f43f3d7@example.com	$2b$12$xm40VGLzu3oTJPlFTvBe9.qlJ5LRyzAguqo8Kod6f8JTzkQzIpvpG	Test	User	consultant	t	f	2025-09-06 05:06:58.667573+00	2025-09-06 05:06:58.667574+00	\N	2025-09-06 05:06:58.665898+00	0	\N
3a056ec2-bc36-4c78-b7a8-987f0f086df6	test_5a869b43@example.com	$2b$12$k3r9k1tf4TZ4qunQguCfX.twYFVXP8ATovnRwVh0xTKttd4XeNTie	Test	User	consultant	t	f	2025-09-06 05:06:59.030517+00	2025-09-06 05:06:59.030518+00	\N	2025-09-06 05:06:59.029313+00	0	\N
cbbd2a89-9ebf-477e-ab6f-343068a7d5f4	test_3ca1ca60@example.com	$2b$12$zHuH4Q13Y/cCGS1bU3Aea.teMEnHDhiSQZMCxD7INwPjuiFoF9ODK	Test	User	consultant	t	f	2025-09-06 05:06:59.548197+00	2025-09-06 05:06:59.549901+00	\N	2025-09-06 05:06:59.719911+00	0	\N
52ffbf06-d27d-402e-9f5f-6124a2c29d31	test_6e71a08f@example.com	$2b$12$KiHiqeUad.XD7bY5jxNeYOmCsEkUiCHGNGxdokkkC.T5./kcOqcUu	Test	User	consultant	t	f	2025-09-06 05:07:00.407558+00	2025-09-06 05:07:01.110235+00	\N	2025-09-06 05:07:00.406253+00	5	2025-09-06 05:37:01.280835+00
7c1105bf-5bb6-4047-b175-5787571928cb	test_8e5ddbca@example.com	$2b$12$VluLwG7DKAddMkAaRHcgkOgQEnDIJFonKPR4lh7wRTHn4poAt1xLe	Test	User	consultant	t	f	2025-09-06 05:07:01.457286+00	2025-09-06 05:07:01.460171+00	\N	2025-09-06 05:07:01.456335+00	5	2025-09-06 05:06:01.459541+00
a9664dc8-707e-448d-9762-1c631c96a870	test_c6fe6346@example.com	$2b$12$gG1gorDB7LFR1wlLuxUS/OrY4OWqmS0KDMGjyi6AvR1.fChcZJ1W2	Test	User	consultant	t	f	2025-09-06 05:07:01.635064+00	2025-09-06 05:07:01.641346+00	\N	2025-09-06 05:07:01.633598+00	0	\N
356e6634-2f51-4567-a57c-f9586aa471c8	test_3e2fd506@example.com	$2b$12$nDSq2GSbVPiYfcwNm5Mc6Oyik0q9E7Nnodw4NZ9kV2aaSABgdAdNS	Test	User	consultant	t	f	2025-09-06 05:07:01.818476+00	2025-09-06 05:07:01.821254+00	2025-09-06 05:07:01.993647+00	2025-09-06 05:07:01.817829+00	0	\N
ac533e40-7609-4f43-b4ec-e99278bf4ad2	test_d6b7cf78@example.com	$2b$12$ddURJ8CwAEcbplwp5j5JYONSiyO3QTsvmsJBzRlLfBULk93UxANs.	Test	User	consultant	t	f	2025-09-06 05:07:02.171846+00	2025-09-06 05:07:02.171848+00	\N	2025-09-06 05:07:02.170769+00	0	\N
47b846d5-d9bb-4eea-8e80-db78613d6e5e	consultant_1533aa90@example.com	$2b$12$pi/iBiqZvv4gkoCJAys9qeS/8iZS5EghYY0ajsZ1Ha1MQqntJ6qUC	Con	Sultant	consultant	t	f	2025-09-06 05:07:02.516339+00	2025-09-06 05:07:02.51634+00	\N	2025-09-06 05:07:02.344397+00	0	\N
9a9cdb73-9cba-47a6-b8c3-8fbcf8a728b9	admin_e25efff4@example.com	$2b$12$l2TcuUQ4cUoV60yutZwj/eltz.rtgZYDVNrd3BkP1FeZQFj3RvzHC	Ad	Min	admin	t	f	2025-09-06 05:07:02.516343+00	2025-09-06 05:07:02.516343+00	\N	2025-09-06 05:07:02.514713+00	0	\N
dd27e687-74dd-4306-b7c1-2f468f1a6e76	test_5856d75e@example.com	$2b$12$xDz4ZyqEJxt4509Z2PA.heHKDyvQfKb7BiwX8Jq7WJgDwIXvbOKZO	Test	User	consultant	t	f	2025-09-06 05:07:02.694174+00	2025-09-06 05:07:02.694176+00	\N	2025-09-06 05:07:02.692621+00	0	\N
a46dbbcc-cebd-4c2a-b841-30b25951ea84	test_9ebfd6cd@example.com	$2b$12$4N33L2YghlG27zyUTWeKaerrLIrV5D1iHDkxdUkuoOEibaToTOjuK	Test	User	consultant	t	f	2025-09-06 05:07:02.871665+00	2025-09-06 05:07:02.871667+00	\N	2025-09-06 05:07:02.870276+00	0	\N
a04a73d0-93b6-4021-b985-811639274a28	test_14df534c@example.com	$2b$12$W6GamZa9FsR.BYWb/8FLLeaz2eSB2JZsWDlre8mUZT.7TaNIWfNOS	Test	User	consultant	t	f	2025-09-06 05:07:03.056162+00	2025-09-06 05:07:03.056164+00	\N	2025-09-06 05:07:03.054736+00	0	\N
11f12b70-f72d-46ac-a3ec-99c741575fa0	valid_f5ff02a6@example.com	$2b$12$QxcyvS4cvKmq2VnY1U7bi.RF8ITAU6kTDcMySfg4jxF9/EjHv9ohC	Test	User	consultant	t	f	2025-09-06 05:07:03.232757+00	2025-09-06 05:07:03.232759+00	\N	2025-09-06 05:07:03.23131+00	0	\N
da1d41c9-f079-491c-872f-08c5c34dbfb3	user_consultant_6f8a4d30@example.com	$2b$12$BM0/fNxd7qjAW79kuoAKw.5JG/vzJB04898fZbbn751.6/J0kfUoC	Test	User	consultant	t	f	2025-09-06 05:07:03.580516+00	2025-09-06 05:07:03.580518+00	\N	2025-09-06 05:07:03.407444+00	0	\N
b6f45a39-1d7f-4ff1-a3d0-e5e1ab71598c	user_admin_f6556b84@example.com	$2b$12$qR1DW1XmxPizqDq6Ald75.9Kg19jW3J2ZirNdwaJxQg0DvxHgeHN2	Test	User	admin	t	f	2025-09-06 05:07:03.580521+00	2025-09-06 05:07:03.580522+00	\N	2025-09-06 05:07:03.578833+00	0	\N
fcef131e-41d9-49ed-8096-8c57d49bdc97	test_user_bb90b7b0@example.com	$2b$12$S7vwx7aI4ODhHZiePxPE8OhJx10pIENxSZnDyo.3Rywhv5NmDUogu	Test	User	consultant	t	f	2025-09-06 05:07:03.939353+00	2025-09-06 05:07:03.939354+00	\N	2025-09-06 05:07:03.938675+00	0	\N
700e3bbf-fda5-4dd0-99ba-0131e70231f1	test_user_153cf8fe@example.com	$2b$12$L/JZ/ojFEkVNAugOEsy5ouqLWjk0jdOlEjBMzg9eQjAQfTU5ixQ4q	Integration	Test	consultant	t	f	2025-09-07 06:19:16.370568+00	2025-09-07 06:19:16.379905+00	2025-09-07 06:19:16.550594+00	2025-09-07 06:19:16.36868+00	0	\N
8e19ab1b-1ed1-4027-910e-8be3c0127910	test_user_25a72d99@example.com	$2b$12$YMmzNzjTqBvw6l/9cyLhBOFqQl7e922LO1rVKoRrBSJVJCN4p7ZDa	Integration	Test	consultant	t	f	2025-09-07 23:49:41.451595+00	2025-09-07 23:49:41.451597+00	\N	2025-09-07 23:49:41.44955+00	0	\N
2ca9086b-f2ae-4018-9ab0-3324ce1b391d	admin@example.com	$2b$12$lR7ARy8S6OKFTJLUmQEt2.w4MojUcSaGPcdW52qPFvkD1IceDotkK	Admin	User	admin	t	f	2025-08-30 23:06:08.999926+00	2025-09-08 13:36:42.577967+00	2025-09-08 13:36:42.775202+00	2025-08-30 23:06:08.998374+00	0	\N
\.


--
-- TOC entry 3359 (class 2606 OID 16424)
-- Name: analysis_requests analysis_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_requests
    ADD CONSTRAINT analysis_requests_pkey PRIMARY KEY (id);


--
-- TOC entry 3364 (class 2606 OID 16442)
-- Name: analysis_results analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_results
    ADD CONSTRAINT analysis_results_pkey PRIMARY KEY (id);


--
-- TOC entry 3390 (class 2606 OID 16586)
-- Name: file_uploads file_uploads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_uploads
    ADD CONSTRAINT file_uploads_pkey PRIMARY KEY (id);


--
-- TOC entry 3375 (class 2606 OID 16476)
-- Name: prompt_history prompt_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompt_history
    ADD CONSTRAINT prompt_history_pkey PRIMARY KEY (id);


--
-- TOC entry 3369 (class 2606 OID 16462)
-- Name: prompts prompts_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_name_key UNIQUE (name);


--
-- TOC entry 3371 (class 2606 OID 16460)
-- Name: prompts prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_pkey PRIMARY KEY (id);


--
-- TOC entry 3386 (class 2606 OID 16547)
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- TOC entry 3388 (class 2606 OID 16549)
-- Name: refresh_tokens refresh_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_hash_key UNIQUE (token_hash);


--
-- TOC entry 3377 (class 2606 OID 16492)
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- TOC entry 3355 (class 2606 OID 16411)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 3357 (class 2606 OID 16409)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3360 (class 1259 OID 16496)
-- Name: idx_analysis_requests_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analysis_requests_created_at ON public.analysis_requests USING btree (created_at DESC);


--
-- TOC entry 3361 (class 1259 OID 16495)
-- Name: idx_analysis_requests_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analysis_requests_status ON public.analysis_requests USING btree (status);


--
-- TOC entry 3362 (class 1259 OID 16494)
-- Name: idx_analysis_requests_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analysis_requests_user_id ON public.analysis_requests USING btree (user_id);


--
-- TOC entry 3365 (class 1259 OID 16497)
-- Name: idx_analysis_results_request_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analysis_results_request_id ON public.analysis_results USING btree (request_id);


--
-- TOC entry 3391 (class 1259 OID 16596)
-- Name: idx_file_uploads_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_file_uploads_created_at ON public.file_uploads USING btree (created_at);


--
-- TOC entry 3392 (class 1259 OID 16594)
-- Name: idx_file_uploads_file_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_file_uploads_file_hash ON public.file_uploads USING btree (file_hash);


--
-- TOC entry 3393 (class 1259 OID 16593)
-- Name: idx_file_uploads_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_file_uploads_status ON public.file_uploads USING btree (status);


--
-- TOC entry 3394 (class 1259 OID 16592)
-- Name: idx_file_uploads_user_id_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_file_uploads_user_id_created_at ON public.file_uploads USING btree (user_id, created_at);


--
-- TOC entry 3395 (class 1259 OID 16595)
-- Name: idx_file_uploads_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_file_uploads_user_status ON public.file_uploads USING btree (user_id, status);


--
-- TOC entry 3372 (class 1259 OID 16500)
-- Name: idx_prompt_history_prompt_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prompt_history_prompt_id ON public.prompt_history USING btree (prompt_id);


--
-- TOC entry 3373 (class 1259 OID 16501)
-- Name: idx_prompt_history_request_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prompt_history_request_id ON public.prompt_history USING btree (request_id);


--
-- TOC entry 3366 (class 1259 OID 16498)
-- Name: idx_prompts_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prompts_name ON public.prompts USING btree (name);


--
-- TOC entry 3367 (class 1259 OID 16499)
-- Name: idx_prompts_type_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prompts_type_active ON public.prompts USING btree (prompt_type, is_active);


--
-- TOC entry 3378 (class 1259 OID 16559)
-- Name: idx_refresh_tokens_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_expires_at ON public.refresh_tokens USING btree (expires_at);


--
-- TOC entry 3379 (class 1259 OID 16557)
-- Name: idx_refresh_tokens_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_session_id ON public.refresh_tokens USING btree (session_id);


--
-- TOC entry 3380 (class 1259 OID 16558)
-- Name: idx_refresh_tokens_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_status ON public.refresh_tokens USING btree (status);


--
-- TOC entry 3381 (class 1259 OID 16556)
-- Name: idx_refresh_tokens_token_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_token_hash ON public.refresh_tokens USING btree (token_hash);


--
-- TOC entry 3382 (class 1259 OID 16555)
-- Name: idx_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- TOC entry 3383 (class 1259 OID 16560)
-- Name: idx_refresh_tokens_user_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_user_session ON public.refresh_tokens USING btree (user_id, session_id);


--
-- TOC entry 3384 (class 1259 OID 16561)
-- Name: idx_refresh_tokens_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_refresh_tokens_user_status ON public.refresh_tokens USING btree (user_id, status);


--
-- TOC entry 3351 (class 1259 OID 16493)
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- TOC entry 3352 (class 1259 OID 16536)
-- Name: idx_users_failed_attempts; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_failed_attempts ON public.users USING btree (failed_login_attempts);


--
-- TOC entry 3353 (class 1259 OID 16535)
-- Name: idx_users_locked_until; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_locked_until ON public.users USING btree (locked_until);


--
-- TOC entry 3406 (class 2620 OID 16565)
-- Name: refresh_tokens trigger_limit_user_sessions; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_limit_user_sessions BEFORE INSERT ON public.refresh_tokens FOR EACH ROW EXECUTE FUNCTION public.limit_user_sessions();


--
-- TOC entry 3407 (class 2620 OID 16602)
-- Name: file_uploads trigger_update_file_upload_timestamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_update_file_upload_timestamp BEFORE UPDATE ON public.file_uploads FOR EACH ROW EXECUTE FUNCTION public.update_file_upload_timestamp();


--
-- TOC entry 3404 (class 2620 OID 16504)
-- Name: analysis_requests update_analysis_requests_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_analysis_requests_updated_at BEFORE UPDATE ON public.analysis_requests FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3405 (class 2620 OID 16505)
-- Name: prompts update_prompts_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON public.prompts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3403 (class 2620 OID 16503)
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3396 (class 2606 OID 16425)
-- Name: analysis_requests analysis_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_requests
    ADD CONSTRAINT analysis_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3397 (class 2606 OID 16443)
-- Name: analysis_results analysis_results_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_results
    ADD CONSTRAINT analysis_results_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.analysis_requests(id) ON DELETE CASCADE;


--
-- TOC entry 3402 (class 2606 OID 16587)
-- Name: file_uploads file_uploads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file_uploads
    ADD CONSTRAINT file_uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3399 (class 2606 OID 16477)
-- Name: prompt_history prompt_history_prompt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompt_history
    ADD CONSTRAINT prompt_history_prompt_id_fkey FOREIGN KEY (prompt_id) REFERENCES public.prompts(id) ON DELETE CASCADE;


--
-- TOC entry 3400 (class 2606 OID 16482)
-- Name: prompt_history prompt_history_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompt_history
    ADD CONSTRAINT prompt_history_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.analysis_requests(id) ON DELETE CASCADE;


--
-- TOC entry 3398 (class 2606 OID 16463)
-- Name: prompts prompts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- TOC entry 3401 (class 2606 OID 16550)
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Completed on 2025-09-09 07:03:21 UTC

--
-- PostgreSQL database dump complete
--

