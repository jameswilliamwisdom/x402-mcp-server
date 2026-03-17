import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  output: 'static',  // explicit — don't rely on default (DEPLOY-01)

  // Use env var — must be set to real URL before Phase 4 deploy
  site: process.env.SITE_URL || 'https://usebismuth.com',

  integrations: [
    starlight({
      title: 'Bismuth',
      description: 'Pay-per-use APIs for AI agents. No API key required — pay per call with USDC on Base.',

      // Dark mode only — no toggle (FOLIOM prevention)
      components: {
        ThemeProvider: './src/components/ForceDarkTheme.astro',
        ThemeSelect: './src/components/EmptyComponent.astro',
      },

      // Brand theming — dual CSS layer
      customCss: [
        './src/styles/global.css',
        './src/styles/starlight.css',
      ],

      // Google Fonts via <link> + OG meta tags
      head: [
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'preconnect',
            href: 'https://fonts.gstatic.com',
            crossorigin: true,
          },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'stylesheet',
            href: 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap',
          },
        },
        // Global OG fallback (per-page overrides via frontmatter head field)
        {
          tag: 'meta',
          attrs: { property: 'og:image', content: `${process.env.SITE_URL || 'https://usebismuth.com'}/og-image.png` },
        },
        {
          tag: 'meta',
          attrs: { name: 'twitter:card', content: 'summary_large_image' },
        },
      ],

      // Manual sidebar for small doc set
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { slug: 'getting-started' },
            { slug: 'wallet-setup' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { slug: 'api-reference' },
          ],
        },
        {
          label: 'APIs',
          items: [
            { slug: 'apis/scraping' },
            { slug: 'apis/file-conversion' },
            { slug: 'apis/web-search' },
            { slug: 'apis/email' },
            { slug: 'apis/audio-transcription' },
          ],
        },
      ],

      favicon: '/logo-mark.png',
    }),
  ],
});
