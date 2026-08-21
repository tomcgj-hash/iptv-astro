import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// 注意：site 域名待用户确认后更新（当前为占位符）
export default defineConfig({
  site: 'https://www.iptv-demo.example.com',
  integrations: [sitemap()],
  server: {
    // 允许任意 Host 访问（用于临时隧道预览；上线后由 Vercel 托管不经过此配置）
    allowedHosts: true,
  },
});
