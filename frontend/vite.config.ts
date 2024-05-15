import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// @ts-ignore
import { fileURLToPath, URL } from 'url';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@router':  fileURLToPath(new URL('./src/router', import.meta.url)),
      '@assets':  fileURLToPath(new URL('./src/assets', import.meta.url)),
      '@components':  fileURLToPath(new URL('./src/components', import.meta.url)),
      '@utils':  fileURLToPath(new URL('./src/utils', import.meta.url)),
      '@store':  fileURLToPath(new URL('./src/store', import.meta.url)),
    }
  }
})
