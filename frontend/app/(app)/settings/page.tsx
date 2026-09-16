"use client";

import {
  Languages,
  LogOut,
  Mic,
  Monitor,
  Moon,
  ShieldCheck,
  Sun,
  UserRound,
  Trash2,
  X,
} from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { signOut } from "firebase/auth";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import { getAuthenticatedUser, getFirebaseAuth } from "@/lib/firebase";
import { deleteAccount, getAccountProfile, getUserSettings, updateUserSettings, type AccountProfile } from "@/services/account.service";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState("English");
  const [notice, setNotice] = useState("");
  const [voice, setVoice] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [profile, setProfile] = useState<AccountProfile | null>(null);
  useEffect(() => {
    void getAuthenticatedUser().then((user) =>
      setEmail(user?.email ?? "Authenticated account"),
    );
    void getAccountProfile().then((item) => {
      setProfile(item);
      setEmail(item.email ?? "Authenticated account");
    }).catch(() => undefined);
    void getUserSettings().then((settings) => {
      setLanguage(settings.language);
      setTheme(settings.theme);
      localStorage.setItem("multisource-language", settings.language);
    }).catch(() => undefined);
    setLanguage(localStorage.getItem("multisource-language") ?? "English");
    setVoice(
      Boolean(
        (
          window as typeof window & {
            SpeechRecognition?: unknown;
            webkitSpeechRecognition?: unknown;
          }
        ).SpeechRecognition ||
          (window as typeof window & { webkitSpeechRecognition?: unknown })
            .webkitSpeechRecognition,
      ),
    );
  }, [setTheme]);
  const updateLanguage = (value: string) => {
    setLanguage(value);
    localStorage.setItem("multisource-language", value);
    void updateUserSettings({ language: value as "English" | "Tamil" | "Hindi" })
      .then(() => setNotice("Language preference saved privately across your devices."))
      .catch((error: Error) => setNotice(error.message));
  };
  const updateTheme = (value: string) => {
    setTheme(value);
    void updateUserSettings({ theme: value as "light" | "dark" | "system" })
      .then(() => setNotice("Theme preference saved privately across your devices."))
      .catch((error: Error) => setNotice(error.message));
  };
  return (
    <div className="settings-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">PRIVACY & PREFERENCES</span>
            <h1>Settings</h1>
            <p>
              Control presentation, language, browser voice, and your
              authenticated session.
            </p>
          </div>
        </header>
      </Reveal>
      {notice && <div className="chat-notice">{notice}</div>}
      <div className="settings-grid">
        <Reveal>
          <section className="settings-card">
            <header>
              <div>
                <UserRound size={19} />
              </div>
              <div>
                <span>ACCOUNT SESSION</span>
                <h2>Authenticated identity</h2>
              </div>
            </header>
            <div className="settings-value">
              <strong>{email}</strong>
              <span>
                Your identity is verified server-side for every private request.
              </span>
              {profile && <div className="account-meta"><i>{profile.email_verified ? "Verified email" : "Email verification pending"}</i><i>{profile.provider?.replaceAll(".", " ") ?? "Firebase"}</i>{profile.is_admin && <i>Administrator</i>}</div>}
            </div>
            <Button
              variant="secondary"
              onClick={() =>
                void signOut(getFirebaseAuth()).then(() =>
                  window.location.assign("/login"),
                )
              }
            >
              <LogOut size={16} /> Sign out
            </Button>
          </section>
        </Reveal>
        <Reveal delay={0.04}>
          <section className="settings-card">
            <header>
              <div>
                <Sun size={19} />
              </div>
              <div>
                <span>APPEARANCE</span>
                <h2>Designed theme</h2>
              </div>
            </header>
            <div className="theme-choices">
              {[
                ["light", Sun, "Light"],
                ["dark", Moon, "Dark"],
                ["system", Monitor, "System"],
              ].map(([id, Icon, label]) => (
                <button
                  key={String(id)}
                  className={theme === id ? "active" : ""}
                  onClick={() => updateTheme(String(id))}
                  aria-pressed={theme === id}
                >
                  <Icon size={17} />
                  <span>{String(label)}</span>
                </button>
              ))}
            </div>
          </section>
        </Reveal>
        <Reveal delay={0.08}>
          <section className="settings-card">
            <header>
              <div>
                <Languages size={19} />
              </div>
              <div>
                <span>LANGUAGE</span>
                <h2>Default interaction</h2>
              </div>
            </header>
            <label className="settings-select">
              Preferred language
              <select
                value={language}
                onChange={(event) => updateLanguage(event.target.value)}
              >
                <option>English</option>
                <option>Tamil</option>
                <option>Hindi</option>
              </select>
            </label>
            <p>
              Individual chat and intelligence tools can still override this
              preference.
            </p>
          </section>
        </Reveal>
        <Reveal delay={0.12}>
          <section className="settings-card security">
            <header>
              <div>
                <Mic size={19} />
              </div>
              <div>
                <span>VOICE PRIVACY</span>
                <h2>Browser-only microphone flow</h2>
              </div>
            </header>
            <div className={`support-state ${voice ? "supported" : "limited"}`}>
              <i>{voice ? "△" : "!"}</i>
              <div>
                <strong>
                  {voice
                    ? "Speech recognition available"
                    : "Recognition unavailable"}
                </strong>
                <span>
                  {voice
                    ? "Spoken audio is converted to text by browser capabilities; this app does not save raw recordings."
                    : "Typed input and read-aloud remain available where supported."}
                </span>
              </div>
            </div>
            <p>AI answers speak only when you click that answer&apos;s speaker button. Playback stops safely when you leave the page.</p>
            <div className="privacy-points">
              <span>
                <ShieldCheck size={14} /> Private by default
              </span>
              <span>
                <ShieldCheck size={14} /> No raw microphone storage
              </span>
              <span>
                <ShieldCheck size={14} /> Server-derived identity
              </span>
            </div>
          </section>
        </Reveal>
        <Reveal delay={0.16}>
          <section className="settings-card danger-zone">
            <header>
              <div>
                <Trash2 size={19} />
              </div>
              <div>
                <span>DATA DELETION</span>
                <h2>Delete account and private data</h2>
              </div>
            </header>
            <p>
              Permanently removes MongoDB records, Qdrant vectors, private
              files, OCR artifacts, caches, and the Firebase account.
            </p>
            <Dialog.Root
              onOpenChange={(open) => {
                if (!open) {
                  setConfirmation("");
                  setDeleteError("");
                }
              }}
            >
              <Dialog.Trigger asChild>
                <Button variant="destructive">
                  <Trash2 size={16} /> Delete account
                </Button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="citation-overlay" />
                <Dialog.Content className="delete-dialog">
                  <div className="delete-dialog-head">
                    <div>
                      <span>IRREVERSIBLE ACTION</span>
                      <Dialog.Title>Delete everything?</Dialog.Title>
                      <Dialog.Description>
                        This cannot be undone. A login within the last 10
                        minutes is required.
                      </Dialog.Description>
                    </div>
                    <Dialog.Close asChild>
                      <Button size="icon" variant="ghost" aria-label="Close">
                        <X size={18} />
                      </Button>
                    </Dialog.Close>
                  </div>
                  <label>
                    Type DELETE to confirm
                    <input
                      value={confirmation}
                      onChange={(e) => setConfirmation(e.target.value)}
                      autoComplete="off"
                    />
                  </label>
                  {deleteError && (
                    <div className="delete-error">{deleteError}</div>
                  )}
                  <div className="delete-actions">
                    <Dialog.Close asChild>
                      <Button variant="secondary">Cancel</Button>
                    </Dialog.Close>
                    <Button
                      variant="destructive"
                      disabled={confirmation !== "DELETE" || deleting}
                      onClick={() => {
                        setDeleting(true);
                        setDeleteError("");
                        void deleteAccount()
                          .then(() => signOut(getFirebaseAuth()))
                          .then(() => window.location.assign("/"))
                          .catch((error: Error) =>
                            setDeleteError(error.message),
                          )
                          .finally(() => setDeleting(false));
                      }}
                    >
                      {deleting ? "Deleting securely…" : "Permanently delete"}
                    </Button>
                  </div>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </section>
        </Reveal>
      </div>
    </div>
  );
}
