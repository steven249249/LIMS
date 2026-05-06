# Two-stage build for production:
#  1) Vite builds the SPA → /app/dist
#  2) Caddy 2 serves the SPA + reverse-proxies /api/* to the Django backend,
#     and automatically obtains + renews a Let's Encrypt cert for HTTPS.
#
# Caddy reads ./Caddyfile from this directory at build time (copied to
# /etc/caddy/Caddyfile inside the image).
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
