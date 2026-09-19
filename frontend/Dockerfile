# ==============================================================================
# AI Smart Traffic Intelligence Platform — Frontend Container
# ==============================================================================
# Multi-stage build:
# Stage 1: Compiles TypeScript and builds production assets with Vite
# Stage 2: Serves static bundle via lightweight Nginx with SPA routing & reverse proxy
# Includes Alpine security updates to patch base image CVEs.
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
FROM nginx:alpine-slim

# Upgrade Alpine base packages to latest security patches and clean default files
RUN apk update && apk upgrade --no-cache && \
    rm -rf /usr/share/nginx/html/*

# Copy built static assets from builder stage (no node_modules or build tools in runtime)
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
