"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export function useSSE(url: string | null) {
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<{ node?: string; step?: string; progress?: number }>({});
  const [messages, setMessages] = useState<string[]>([]);
  const [phase, setPhase] = useState<{ phase?: string; redirect?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);
  const maxRetries = 3;

  const connect = useCallback(() => {
    if (!url) return;

    const es = new EventSource(url);
    esRef.current = es;
    setConnected(true);
    retriesRef.current = 0;

    es.addEventListener("log", (e) => {
      setLogs((prev) => {
        const next = [...prev, e.data];
        return next.length > 500 ? next.slice(-300) : next;
      });
    });

    es.addEventListener("status", (e) => {
      try { setStatus(JSON.parse(e.data)); } catch {}
    });

    es.addEventListener("message", (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.text) setMessages((prev) => [...prev, d.text]);
      } catch {}
    });

    es.addEventListener("phase", (e) => {
      try { setPhase(JSON.parse(e.data)); } catch {}
      es.close();
      setConnected(false);
    });

    es.addEventListener("error", (e) => {
      if (e instanceof MessageEvent) {
        try {
          const d = JSON.parse(e.data);
          setError(d.message || "Unknown error");
        } catch {}
      }
      es.close();
      setConnected(false);
    });

    es.addEventListener("done", () => {
      es.close();
      setConnected(false);
    });

    es.onerror = () => {
      es.close();
      setConnected(false);

      // Auto-reconnect on connection loss (not on explicit close/error)
      if (!phase && !error && retriesRef.current < maxRetries) {
        retriesRef.current++;
        const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 10000);
        setTimeout(() => connect(), delay);
      }
    };
  }, [url, phase, error]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      setConnected(false);
    };
  }, [connect]);

  const reset = useCallback(() => {
    setLogs([]);
    setStatus({});
    setMessages([]);
    setPhase(null);
    setError(null);
  }, []);

  return { logs, status, messages, phase, error, connected, reset };
}
