import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Peach Finder — Universal Video Hub",
  description:
    "Temukan, analisis, dan unduh media yang diizinkan dari internet, lalu simpan ke perpustakaan pribadimu.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
