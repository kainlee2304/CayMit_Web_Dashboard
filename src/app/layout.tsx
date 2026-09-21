import type { Metadata, Viewport } from "next";
import "./globals.css";
import { CaptureProvider } from "@/context/CaptureContext";
import { AuthProvider } from "@/context/AuthContext";
import { LanguageProvider } from "@/context/LanguageContext";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Tam Mỹ Smart Fruit - Hệ sinh thái Chuỗi giá trị Nông nghiệp",
  description: "Hệ thống quản trị số Vùng trồng, Thửa đất, Chuỗi cung ứng Mít và Thẩm định Bảo chứng",
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
      <body className="min-h-dvh overflow-x-hidden bg-gray-950 text-gray-100 font-sans antialiased">
        <LanguageProvider>
          <AuthProvider>
            <CaptureProvider>
              <AppShell>{children}</AppShell>
            </CaptureProvider>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
