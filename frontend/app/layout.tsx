import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HuggingFace Course RAG",
  description: "Multimodal RAG system over HuggingFace Learn courses",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
