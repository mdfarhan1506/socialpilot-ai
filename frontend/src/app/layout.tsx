import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'SocialPilot AI',
  description: 'AI-powered social media management',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
