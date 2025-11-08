// frontend/vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // This will proxy any request starting with /api OR /authorize OR /callback
      // to your backend server running on http://localhost:8000
      '^/api/.*|^/authorize|^/callback': { // This covers /api/schedule-interview and /api/upcoming-interviews
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})