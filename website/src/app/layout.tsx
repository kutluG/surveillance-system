import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { Toaster } from "@/components/ui/toaster"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: {
    default: "SecureWatch AI - AI-Powered Video Surveillance",
    template: "%s | SecureWatch AI"
  },
  description: "Advanced AI-powered video surveillance solutions for modern security needs. Real-time alerts, custom scenarios, and GDPR-compliant monitoring.",
  keywords: ["AI surveillance", "video monitoring", "security", "real-time alerts", "GDPR compliant"],
  authors: [{ name: "SecureWatch AI" }],
  creator: "SecureWatch AI",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://securewatch-ai.com",
    title: "SecureWatch AI - AI-Powered Video Surveillance",
    description: "Advanced AI-powered video surveillance solutions for modern security needs.",
    siteName: "SecureWatch AI",
  },
  twitter: {
    card: "summary_large_image",
    title: "SecureWatch AI - AI-Powered Video Surveillance",
    description: "Advanced AI-powered video surveillance solutions for modern security needs.",
    creator: "@securewatchai",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="relative flex min-h-screen flex-col">
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
