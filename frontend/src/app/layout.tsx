import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Digi-Biz - Business Digitization",
  description: "Transform your business documents into a beautiful digital profile",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
