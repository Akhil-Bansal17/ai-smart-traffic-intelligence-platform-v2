# ==============================================================================
# AI Smart Traffic Intelligence Platform — Frontend Container
# ==============================================================================
# Multi-stage build:
# Stage 1: Compiles TypeScript and builds production assets with Vite
# Stage 2: Serves static bundle via lightweight Nginx with SPA routing & reverse proxy
# ==============================================================================

# --- Stage 1: Build Environment ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci 2>/dev/null || npm install

COPY frontend ./

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- Stage 2: Production Web Server ---
FROM nginx:alpine

# Remove default nginx html
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
