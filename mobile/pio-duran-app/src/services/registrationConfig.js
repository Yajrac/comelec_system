import { API_BASE_URL as API } from "./apiConfig";
import axios from "axios";
import { Preferences } from "@capacitor/preferences";


const key = `registration-config:${API}`;
export async function loadRegistrationConfig() {
    try {
        const { data } = await axios.get(`${API}/api/registration-config/`, { timeout: 10000 });
        if (!/^\d{4}-\d{2}-\d{2}$/.test(data.election_date)) throw new Error("Invalid election date.");
        await Preferences.set({ key, value: JSON.stringify(data) });
        return data;
    } catch {
        const { value } = await Preferences.get({ key });
        if (value) return JSON.parse(value);
        throw new Error("Connect to the server once to download election settings before registering offline.");
    }
}
