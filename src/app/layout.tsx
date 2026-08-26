import type { Metadata, Viewport } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { CaptureProvider } from "@/context/CaptureContext";
import AutoCaptureToast from "@/components/AutoCaptureToast";

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
        <CaptureProvider>
          <div className="flex min-h-dvh min-w-0 flex-col lg:h-dvh lg:flex-row lg:overflow-hidden">
            <Sidebar />
            <main className="min-w-0 flex-1 overflow-x-hidden px-3 py-4 sm:p-6 lg:overflow-y-auto">
              {children}
            </main>
          </div>
          {/* Floating toast - hiện khi auto-capture bật dù ở trang nào */}
          <AutoCaptureToast />
        </CaptureProvider>
      </body>
    </html>
  );
}
