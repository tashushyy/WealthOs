import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Coded Mind",
  description: "Plan your investments, independence, and withdrawals.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-black text-white antialiased">
        {children}
      </body>
    </html>
  );
}
