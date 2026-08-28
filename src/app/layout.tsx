import type { Metadata, Viewport } from "next";
import "./globals.css";
import { CaptureProvider } from "@/context/CaptureContext";
import { AuthProvider } from "@/context/AuthContext";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "CayMit - Phát Hiện Bệnh Cây",
  description: "Hệ thống AI giám sát và phát hiện bệnh cây Mít thông minh",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="min-h-dvh overflow-x-hidden bg-gray-950 text-gray-100">
        <AuthProvider><CaptureProvider><AppShell>{children}</AppShell></CaptureProvider></AuthProvider>
      </body>
    </html>
  );
}
