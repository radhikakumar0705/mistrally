# syntax=docker/dockerfile:1

# ---- Build stage: compile the React app ----
FROM node:22.11.0-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- Runtime stage: static files served by unprivileged nginx ----
FROM nginxinc/nginx-unprivileged:1.27.3-alpine

# Where nginx proxies /api; rendered into the config at container start
ENV BACKEND_URL=http://backend:5000

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
