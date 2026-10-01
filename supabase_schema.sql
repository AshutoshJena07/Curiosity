-- =====================================================================
-- CURIOSITY AI: SUPABASE SCHEMA SETUP
-- Run this in your Supabase SQL Editor (supabase.com/dashboard)
-- =====================================================================

-- 1. Create Conversations Table
CREATE TABLE IF NOT EXISTS public.conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Untitled Session',
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    attachments JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create Fast Search Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON public.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON public.conversations(updated_at DESC);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- 4. Create Access Policies (Allows seamless cloud sync)
DROP POLICY IF EXISTS "Allow all access to conversations" ON public.conversations;
CREATE POLICY "Allow all access to conversations" 
ON public.conversations
FOR ALL
USING (true)
WITH CHECK (true);

-- 5. Create Storage Bucket for chat attachments / images (optional)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('chat-attachments', 'chat-attachments', true)
ON CONFLICT (id) DO NOTHING;

-- 6. Storage Bucket Policy
DROP POLICY IF EXISTS "Public Access for Chat Attachments" ON storage.objects;
CREATE POLICY "Public Access for Chat Attachments" 
ON storage.objects 
FOR ALL 
USING (bucket_id = 'chat-attachments')
WITH CHECK (bucket_id = 'chat-attachments');
