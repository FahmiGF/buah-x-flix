import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "My Netflix — Universal Video Hub",
  description: "Perpustakaan video pribadi dengan pengalaman browsing sinematik.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
