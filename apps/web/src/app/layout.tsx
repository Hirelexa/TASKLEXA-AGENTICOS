import type { Metadata } from "next";
import { TopNav } from "@/components/top-nav";
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
      <body className="bg-[#f6f7f9] text-slate-950">
        <TopNav />
        {children}
      </body>
    </html>
  );
}

