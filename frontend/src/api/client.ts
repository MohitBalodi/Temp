import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

import { tokenStore } from '@/lib/tokens';

import type { components } from './schema';

export type TokenPair = components['schemas']['TokenPair'];
export type UserOut = components['schemas']['UserOut'];
export type LoginRequest = components['schemas']['LoginRequest'];

// Relative by default: the Vite dev server proxies /api to the API, so the
// browser only ever talks to the origin it loaded from. Set
// VITE_API_BASE_URL to an absolute URL to bypass the proxy.
const baseURL = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/v1`;

export const api = axios.create({ baseURL });

// Fired when the session can't be recovered (refresh failed). The app listens
// and sends the user to /login.
export const SESSION_EXPIRED_EVENT = 'ava:session-expired';

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// One in-flight refresh shared by every request that hit a 401 at the same time.
let refreshing: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh_token = tokenStore.getRefresh();
  if (!refresh_token) throw new Error('no refresh token');
  // Plain axios (not `api`) so this call doesn't go through the interceptors.
  const { data } = await axios.post<TokenPair>(`${baseURL}/auth/refresh`, { refresh_token });
  tokenStore.set(data);
  return data.access_token;
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const isAuthCall = config?.url?.startsWith('/auth/login') || config?.url?.startsWith('/auth/refresh');

    if (error.response?.status !== 401 || !config || config._retried || isAuthCall) {
      throw error;
    }

    try {
      refreshing ??= refreshAccessToken().finally(() => {
        refreshing = null;
      });
      const token = await refreshing;
      config._retried = true;
      config.headers.Authorization = `Bearer ${token}`;
      return api(config);
    } catch {
      tokenStore.clear();
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      throw error;
    }
  },
);

/** Pull the `{"error": {"message"}}` envelope out of an API error. */
export function apiErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (axios.isAxiosError(error)) {
    const message = (error.response?.data as { error?: { message?: string } } | undefined)?.error
      ?.message;
    if (message) return message;
    if (!error.response) return 'Cannot reach the server.';
  }
  return fallback;
}

/**
 * Per-field messages from a 422 `validation_error`, keyed by field name
 * (e.g. `{ cgpa: "..." }`). Errors not tied to one field go under `_form`.
 */
export function apiFieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error)) return {};
  const fields = (
    error.response?.data as
      | { error?: { fields?: { loc: (string | number)[]; msg: string }[] } }
      | undefined
  )?.error?.fields;
  const out: Record<string, string> = {};
  for (const f of fields ?? []) {
    // loc is ["body", "<field>"] for field errors, ["body"] for whole-body ones.
    const key = f.loc.length > 1 ? String(f.loc[f.loc.length - 1]) : '_form';
    out[key] ??= f.msg.replace(/^Value error, /, '');
  }
  return out;
}
