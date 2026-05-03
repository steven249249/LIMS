import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
// Vitest configuration lives in vitest.config.js — keeping the build config
// minimal here.
export default defineConfig({
  plugins: [vue()],
})
