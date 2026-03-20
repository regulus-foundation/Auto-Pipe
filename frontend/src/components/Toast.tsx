"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface Toast {
  id: number;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastContextType {
  toast: (message: string, type?: Toast["type"]) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let counter = 0;

  const toast = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = ++counter;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const colors = {
    success: { bg: "rgba(34,197,94,0.15)", border: "rgba(34,197,94,0.3)", text: "#4ADE80" },
    error: { bg: "rgba(239,68,68,0.15)", border: "rgba(239,68,68,0.3)", text: "#F87171" },
    info: { bg: "rgba(59,130,246,0.15)", border: "rgba(59,130,246,0.3)", text: "#60A5FA" },
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 right-6 space-y-2 z-50">
        {toasts.map((t) => {
          const c = colors[t.type];
          return (
            <div
              key={t.id}
              className="px-4 py-3 rounded-lg text-sm font-medium animate-fade-in min-w-[300px]"
              style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text }}
            >
              {t.message}
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
