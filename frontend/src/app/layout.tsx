import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SocialPilot AI - Social Media Management',
  description: 'AI-powered social media management, scheduling, and analytics platform.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
