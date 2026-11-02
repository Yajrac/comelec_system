// Vite reads this setting from the mobile app folder at build time.
// Use the server origin only; endpoints already include /api/.
const configuredUrl = (import.meta.env.VITE_API_URL || '').trim();
export const API_BASE_URL = (configuredUrl || 'http://localhost:8000').replace(/\/+$/, '');
