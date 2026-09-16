"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type VoiceState = "idle" | "listening" | "speaking" | "error";
type RecognitionEvent = { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> };
type RecognitionInstance = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: RecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};
type RecognitionConstructor = new () => RecognitionInstance;

const speechLanguage = { English: "en-IN", Tamil: "ta-IN", Hindi: "hi-IN" } as const;

function spokenLanguage(text: string, selected: keyof typeof speechLanguage) {
  if (/[\u0B80-\u0BFF]/u.test(text)) return "ta-IN";
  if (/[\u0900-\u097F]/u.test(text)) return "hi-IN";
  return speechLanguage[selected];
}

function cleanForSpeech(text: string) {
  return text
    .replace(/```[\s\S]*?```/g, " Code example omitted. ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)]\([^)]*\)/g, "$1")
    .replace(/\[(S\d+)]/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/[*_~>|]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function speechChunks(text: string, limit = 220) {
  const sentences = cleanForSpeech(text).match(/[^.!?।]+[.!?।]?/g) ?? [];
  const chunks: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    const value = sentence.trim();
    if (!value) continue;
    if (`${current} ${value}`.trim().length <= limit) {
      current = `${current} ${value}`.trim();
      continue;
    }
    if (current) chunks.push(current);
    if (value.length <= limit) {
      current = value;
      continue;
    }
    const words = value.split(/\s+/);
    current = "";
    for (const word of words) {
      if (`${current} ${word}`.trim().length > limit && current) {
        chunks.push(current);
        current = word;
      } else current = `${current} ${word}`.trim();
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

export function useVoice(language: keyof typeof speechLanguage) {
  const [state, setState] = useState<VoiceState>("idle");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const recognition = useRef<RecognitionInstance | null>(null);
  const speechSession = useRef(0);
  const recognitionSupported = typeof window !== "undefined" && Boolean(
    (window as typeof window & { SpeechRecognition?: RecognitionConstructor }).SpeechRecognition ||
    (window as typeof window & { webkitSpeechRecognition?: RecognitionConstructor }).webkitSpeechRecognition,
  );
  const speechSupported = typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;

  const stopListening = useCallback(() => {
    recognition.current?.stop();
    recognition.current = null;
    setState((value) => (value === "listening" ? "idle" : value));
  }, []);

  const startListening = useCallback((onText: (text: string) => void) => {
    setError("");
    if (!recognitionSupported) {
      setError("Speech recognition is not supported by this browser. You can still type your question.");
      setState("error");
      return;
    }
    const scope = window as typeof window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
    const Constructor = scope.SpeechRecognition ?? scope.webkitSpeechRecognition;
    if (!Constructor) return;
    recognition.current?.abort();
    const instance = new Constructor();
    instance.lang = speechLanguage[language];
    instance.interimResults = true;
    instance.continuous = false;
    instance.onresult = (event) => {
      let text = "";
      for (let index = 0; index < event.results.length; index++) text += event.results[index][0].transcript;
      onText(text.trim());
    };
    instance.onerror = () => {
      setError("Could not understand the microphone input. Please retry or type your question.");
      setState("error");
    };
    instance.onend = () => {
      recognition.current = null;
      setState((value) => (value === "listening" ? "idle" : value));
    };
    recognition.current = instance;
    instance.start();
    setState("listening");
  }, [language, recognitionSupported]);

  const stopSpeaking = useCallback(() => {
    speechSession.current += 1;
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    setActiveId(null);
    setState("idle");
  }, []);

  const speak = useCallback((text: string, messageId: string) => {
    setError("");
    if (!speechSupported) {
      setError("Read aloud is not supported by this browser.");
      setState("error");
      return;
    }
    const chunks = speechChunks(text);
    if (!chunks.length) return;
    const session = speechSession.current + 1;
    speechSession.current = session;
    window.speechSynthesis.cancel();
    setActiveId(messageId);
    setState("speaking");
    let index = 0;
    const next = () => {
      if (speechSession.current !== session || index >= chunks.length) {
        if (speechSession.current === session) {
          setActiveId(null);
          setState("idle");
        }
        return;
      }
      const utterance = new SpeechSynthesisUtterance(chunks[index++]);
      utterance.lang = spokenLanguage(utterance.text, language);
      const voice = window.speechSynthesis.getVoices().find((item) =>
        item.lang.toLowerCase().startsWith(utterance.lang.slice(0, 2).toLowerCase()),
      );
      if (voice) utterance.voice = voice;
      utterance.rate = 1;
      utterance.onend = next;
      utterance.onerror = (event) => {
        if (speechSession.current !== session || event.error === "canceled" || event.error === "interrupted") return;
        setError("This answer could not be read aloud.");
        setActiveId(null);
        setState("error");
      };
      window.speechSynthesis.speak(utterance);
    };
    next();
  }, [language, speechSupported]);

  useEffect(() => () => {
    recognition.current?.abort();
    speechSession.current += 1;
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  return { state, activeId, error, recognitionSupported, speechSupported, startListening, stopListening, speak, stopSpeaking };
}
