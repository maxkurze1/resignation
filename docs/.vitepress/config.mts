import { defineConfig } from 'vitepress'
import Tailwind from '@tailwindcss/vite'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "re[sign]ation",
  base: "/resignation/",
  description: "A script to create digital signatures",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Reference', link: '/cli' }
    ],

    sidebar: [
      {
        text: 'Reference',
        items: [
          { text: 'Command Line Interface', link: '/cli' },
          { text: 'Config Options', link: '/config' },
          { text: 'Templates', link: '/templates' },
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/maxkurze1/resignation' }
    ]
  },
  vite: {
    plugins: [
      Tailwind()
    ]
  }
})
