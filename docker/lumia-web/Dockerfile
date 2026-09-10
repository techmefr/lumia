FROM node:24.21.0-alpine AS build
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile
# Relative base url: nginx serves the app and proxies /api to the backend, so the bundle
# never carries a hostname that only works on one machine.
ENV VITE_API_BASE_URL=/api
RUN pnpm --filter web build

FROM nginx:1.27.5-alpine
COPY docker/lumia-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/apps/web/build /usr/share/nginx/html
