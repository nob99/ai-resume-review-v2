'use client'

import { useEffect } from "react";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  useEffect(() => {
    console.log(`
%c
  ██╗  ██╗███████╗██╗     ██╗      ██████╗
  ██║  ██║██╔════╝██║     ██║     ██╔═══██╗
  ███████║█████╗  ██║     ██║     ██║   ██║
  ██╔══██║██╔══╝  ██║     ██║     ██║   ██║
  ██║  ██║███████╗███████╗███████╗╚██████╔╝
  ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝

%cWELCOME TO YATAGARASU - Resume Review AI Multi Agents System
`,
      'color: #3B82F6; font-weight: bold;',
      'color: #000000; font-size: 16px; font-weight: bold;'
    );
  }, []);

  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <AuthProvider>
          <ToastProvider position="bottom-right">
            {children}
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
