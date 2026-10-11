import type { Metadata } from "next";
import { Inter, Lexend } from "next/font/google";
import "./globals.css";

const body = Inter({ variable: "--font-body", subsets: ["latin"] });
const heading = Lexend({ variable: "--font-heading", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Study Hub",
  description: "Verified CBSE Class 10 study materials and practice",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${body.variable} ${heading.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
