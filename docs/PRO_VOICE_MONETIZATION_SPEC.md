# 🎙️ Feature Specification: Ultra-Realistic Pro Voice Studio & UPI Monetization

> **Status**: Planned / Ready for Implementation  
> **Trigger Prompt**: `"Implement Pro Voice Studio with 5 Cartesia voices, 5-use quota meter, auto-fallback, and ₹519 UPI QR payment flow as documented in docs/PRO_VOICE_MONETIZATION_SPEC.md"`

---

## 1. Overview & Business Strategy
- **Freemium Voice Model**:
  - Browser Native Voices (Google, Microsoft) remain **100% Free and Unlimited**.
  - Cartesia Ultra-Realistic Voice Models are **PRO Features** capped at **5 free trial generations per user**.
- **User Experience**:
  - No complex payment gateway KYC/chargeback hassle.
  - Payment collected directly via **UPI QR Code (₹519 / 1 Month)**.
  - Transparent live usage meter (0% to 100%).
  - Graceful auto-fallback to default native voices once quota finishes (no chat break).
  - Admin approval/activation flow (10-15 min ETA notice to user).

---

## 2. Curated Voice Models (5 Cartesia Voices)
Provide 5 curated Male & Female Ultra-Realistic AI voices in the dropdown:
1. **Aditi (Ultra-Realistic Indian Female - hi-IN)**
2. **Pooja (Expressive Hinglish Female - hi-IN)**
3. **Kabir (Deep & Natural Indian Male - hi-IN)**
4. **Rohan (Conversational Hinglish Male - hi-IN)**
5. **Studio Narrator (High-Fidelity Neutral - en-IN/hi-IN)**

---

## 3. Usage Meter & Side Panel UI
- Located in **Voice Studio Settings** drawer.
- Shows live quota:
  - Format: `X / 5 Free Uses Generated (Y%)`
  - Dynamic Progress Bar:
    - 0% - 60%: Green/Accent
    - 80%: Warning Orange (1 use remaining)
    - 100%: Red Alert (Quota Exhausted)

---

## 4. Quota Exhaustion & Auto-Fallback Flow
- When user reaches 5/5 uses (100%):
  - Model selection automatically falls back to default browser voice so audio playback doesn't freeze.
  - A modal/popup appears:
    - **Header**: "🌟 Unlock Pro Voice Studio"
    - **Message**: "Pay ₹519 / 1 Month to continue using Ultra-Realistic Voice Models."
    - **CTA Button**: "Proceed to QR Payment"

---

## 5. UPI QR Code Modal & Payment Submission
- When CTA button is clicked:
  - Shows dynamic/static UPI QR Code for ₹519.
  - Displays UPI ID and instructions (PhonePe / GPay / Paytm).
  - Input field for **UPI Transaction ID / UTR number**.
  - **"I Have Paid"** confirmation button.
- On submit:
  - Green checkmark confirmation screen:
    - *"Payment Submitted Successfully!"*
    - *"Your transaction is being verified. Your Ultra-Realistic voices will be activated within 10–15 minutes."*
  - Saves pending payment request to database (`payment_requests` table).

---

## 6. Admin Control & Pro Activation
- Backend database tracks:
  - `is_pro` (0 or 1)
  - `pro_voice_usage` (integer)
  - `pro_expires_at` (datetime)
- Admin can approve user via simple endpoint or admin toggle:
  - `/api/admin/activate-pro?user_id=...&days=30`
- Once active:
  - Voice usage changes to **"🌟 Unlimited Pro Active"**.
  - All 5 Cartesia voices unlocked without quota limits.
