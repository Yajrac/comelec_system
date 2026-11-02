import { API_BASE_URL as API } from "./apiConfig";
import axios from "axios";
import { Preferences } from "@capacitor/preferences";
import { Network } from "@capacitor/network";


const KEY = `barangays:${API}`;
export async function loadCachedBarangays() {
    const { value } = await Preferences.get({ key: KEY });
    const cached = value ? JSON.parse(value) : [];
    let connected = navigator.onLine;
    try { connected = (await Network.getStatus()).connected; } catch { /* Browser fallback. */ }
    if (connected) {
        try {
            const { data } = await axios.get(`${API}/api/barangays/`, { timeout: 10000 });
            if (!Array.isArray(data) || !data.length) throw new Error("No barangays available.");
            await Preferences.set({ key: KEY, value: JSON.stringify(data) });
            return data;
        } catch (error) {
            if (!cached.length) throw error;
        }
    }
    if (!cached.length) throw new Error("Connect to the internet once to download the barangay list before registering offline.");
    return cached;
}
