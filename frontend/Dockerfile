# Front-end em modo de desenvolvimento (Vite). O build de produção entra no sprint 14.
FROM node:22-alpine

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
EXPOSE 5173
CMD ["pnpm", "dev"]
