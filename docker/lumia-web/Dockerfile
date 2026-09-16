FROM node:26.8-alpine AS build
# Node 26 ships without corepack, so enabling it straight away exits 127. Installing it is
# still the way to honour the packageManager field rather than guessing a pnpm version.
RUN npm install --global corepack@latest && corepack enable
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile
# Relative base url: nginx serves the app and proxies /api to the backend, so the bundle
# never carries a hostname that only works on one machine.
ENV VITE_API_BASE_URL=/api
RUN pnpm --filter web build

FROM nginx:1.31.5-alpine

# Templated rather than copied to conf.d: the image is published, so the backend it proxies to
# cannot be a name that only resolves inside this repository's compose file. The default keeps
# docker-compose.yml working untouched.
ENV LUMIA_BACKEND_URL=http://lumia-backend-api:8000
# Without the filter, envsubst would also eat nginx's own $host, $uri and $scheme.
ENV NGINX_ENVSUBST_FILTER=^LUMIA_

COPY docker/lumia-web/templates/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker/lumia-web/security-headers.conf /etc/nginx/conf.d/security-headers.conf
COPY --from=build /repo/apps/web/build /usr/share/nginx/html

# Unprivileged: port 8080 rather than 80, since a non-root process cannot bind below 1024.
# The entrypoint renders the template and nginx writes its pid and caches, so those paths
# belong to the runtime user.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080
