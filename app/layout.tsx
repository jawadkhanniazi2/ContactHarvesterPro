import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Free Email Scraper Tool - Extract Emails from Websites',
  description: 'Free unlimited email scraper tool. Extract email addresses, phone numbers, and social media links from any website. No signup required, completely free to use.',
  keywords: 'email scraper, email extractor, contact finder, lead generation, free tool',
  authors: [{ name: 'Email Scraper Tool' }],
  openGraph: {
    title: 'Free Email Scraper Tool - Extract Emails from Websites',
    description: 'Free unlimited email scraper tool. Extract email addresses, phone numbers, and social media links from any website.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Free Email Scraper Tool',
    description: 'Free unlimited email scraper tool. Extract emails from any website.',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
          {children}
        </div>
      </body>
    </html>
  )
}