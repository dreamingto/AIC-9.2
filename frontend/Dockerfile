ARG NODE_IMAGE=public.ecr.aws/docker/library/node:22-alpine
ARG NGINX_IMAGE=public.ecr.aws/docker/library/nginx:alpine

FROM ${NODE_IMAGE} AS builder
WORKDIR /app
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
  npm ci --prefer-offline --no-audit --no-fund
COPY . .
RUN npm run build

FROM ${NGINX_IMAGE}
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# healthcheck needs curl or wget. alpine nginx has wget.
HEALTHCHECK --interval=5s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
