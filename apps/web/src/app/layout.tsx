import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tasklexa Agenticos",
  description: "One Goal. The Right Agents. Governed Execution.",
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

