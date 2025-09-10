import { UniversalToaster } from '@/components/ui/universal-toaster'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Agent Communication Interface',
  description: 'Universal agent communication system with Supabase authentication and real-time chat',
  keywords: ['agents', 'communication', 'AI', 'chat', 'automation'],
  authors: [{ name: 'Agent Communication Team' }],
  viewport: {
    width: 'device-width',
    initialScale: 1,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#3b82f6" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          {children}
        </div>
        <UniversalToaster />
      </body>
    </html>
  )
} 