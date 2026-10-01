// Supabase Cloud Client & Storage Integration

export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://ilzaltvxvtyyfphbtyyj.supabase.co';
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_QM9RhFbfVrOjiZISsYSMPg_oHdhTqf4';

/**
 * Upload chat attachment (image/document) to Supabase Storage Bucket
 * Bucket: chat-attachments
 */
export async function uploadChatAttachmentToSupabase(file, conversationId = 'default') {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !file) return null;

  try {
    const cleanFileName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
    const filePath = `${conversationId}/${Date.now()}_${cleanFileName}`;
    const uploadUrl = `${SUPABASE_URL}/storage/v1/object/chat-attachments/${filePath}`;

    const response = await fetch(uploadUrl, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': file.type || 'application/octet-stream'
      },
      body: file
    });

    if (response.ok) {
      // Returns public URL
      return `${SUPABASE_URL}/storage/v1/object/public/chat-attachments/${filePath}`;
    }
  } catch (err) {
    console.warn('Supabase attachment upload notice:', err);
  }
  return null;
}
