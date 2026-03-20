import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import CommandPalette from "@/components/CommandPalette";
import { ToastProvider } from "@/components/Toast";

export const metadata: Metadata = {
  title: "Auto-Pipe",
  description: "Development Automation Pipeline",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="dark">
      <body className="min-h-screen flex">
        <ToastProvider>
          <Sidebar />
          <main className="ml-60 flex-1 p-8">{children}</main>
          <CommandPalette />
        </ToastProvider>
      </body>
    </html>
  );
}
