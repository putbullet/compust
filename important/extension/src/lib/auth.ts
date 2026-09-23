import { browserAPI } from './browserPolyfill';
import { UserProfile, ExtensionSettings } from './types';

const TOKEN_KEY = 'compust_jwt_token';
const USER_KEY = 'compust_user_profile';
const SETTINGS_KEY = 'compust_settings';

export const DEFAULT_BACKEND_URL = 'http://localhost:8000';

export async function getToken(): Promise<string | null> {
  const result = await browserAPI.storage.local.get<Record<string, any>>(TOKEN_KEY);
  return result[TOKEN_KEY] || null;
}

export async function setToken(token: string): Promise<void> {
  await browserAPI.storage.local.set({ [TOKEN_KEY]: token });
}

export async function removeToken(): Promise<void> {
  await browserAPI.storage.local.remove([TOKEN_KEY, USER_KEY]);
}

export async function getUser(): Promise<UserProfile | null> {
  const result = await browserAPI.storage.local.get<Record<string, any>>(USER_KEY);
  return result[USER_KEY] || null;
}

export async function setUser(user: UserProfile): Promise<void> {
  await browserAPI.storage.local.set({ [USER_KEY]: user });
}

export async function getSettings(): Promise<ExtensionSettings> {
  const result = await browserAPI.storage.local.get<Record<string, any>>(SETTINGS_KEY);
  const saved = result[SETTINGS_KEY];
  return {
    backendUrl: saved?.backendUrl?.replace(/\/+$/, '') || DEFAULT_BACKEND_URL,
  };
}

export async function saveSettings(settings: ExtensionSettings): Promise<void> {
  const normalized = {
    backendUrl: (settings.backendUrl || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, ''),
  };
  await browserAPI.storage.local.set({ [SETTINGS_KEY]: normalized });
}
