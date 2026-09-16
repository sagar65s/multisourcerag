import { apiFetch } from "@/services/api";

export type AccountProfile = {
  uid: string;
  email: string | null;
  display_name: string | null;
  photo_url: string | null;
  provider: string | null;
  email_verified: boolean;
  is_admin: boolean;
  created_at: string;
  last_login_at: string;
};

export type UserSettings = {
  theme: "light" | "dark" | "system";
  language: "English" | "Tamil" | "Hindi";
  updated_at: string;
};

export const syncAccountSession = () =>
  apiFetch<AccountProfile>("/account/session", { method: "POST" }, 8_000);

export const getAccountProfile = () => apiFetch<AccountProfile>("/account");

export const getUserSettings = () => apiFetch<UserSettings>("/account/settings");

export const updateUserSettings = (changes: Partial<Pick<UserSettings, "theme" | "language">>) =>
  apiFetch<UserSettings>("/account/settings", { method: "PATCH", body: JSON.stringify(changes) });

export const deleteAccount = () =>
  apiFetch<void>("/account", {
    method: "DELETE",
    body: JSON.stringify({ confirmation: "DELETE" }),
  });
