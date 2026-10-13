import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import { AppShell } from '@/components/AppShell'
import { CallbackHandler } from '@/components/CallbackHandler'
import { IdentityProvider } from '@/lib/identity-context'

import '../styles.css'

const siteName = 'NFSU Smart Timetable'
const siteDescription =
  'Constraint-aware academic timetabling for the School of Cyber Security & Digital Forensics, National Forensic Sciences University.'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: siteName,
      },
      {
        name: 'description',
        content: siteDescription,
      },
      {
        name: 'theme-color',
        content: '#f6f3ec',
      },
      {
        property: 'og:title',
        content: siteName,
      },
      {
        property: 'og:description',
        content: siteDescription,
      },
      {
        property: 'og:type',
        content: 'website',
      },
      {
        name: 'twitter:card',
        content: 'summary_large_image',
      },
    ],
    links: [
      { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..700,0..100&family=Instrument+Sans:wght@400..700&family=JetBrains+Mono:wght@400;500&display=swap',
      },
    ],
  }),
  shellComponent: RootDocument,
  notFoundComponent: () => (
    <div className="mx-auto max-w-md py-32 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Error 404</p>
      <h1 className="mt-3 font-serif text-4xl">This page isn’t on the timetable.</h1>
      <a href="/" className="mt-6 inline-block text-sm font-medium text-oxblood underline underline-offset-4">
        Back to overview
      </a>
    </div>
  ),
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        <IdentityProvider>
          <CallbackHandler>
            <AppShell>{children}</AppShell>
          </CallbackHandler>
        </IdentityProvider>
        <Scripts />
      </body>
    </html>
  )
}
