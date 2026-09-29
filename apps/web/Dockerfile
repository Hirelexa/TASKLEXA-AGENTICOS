FROM node:24-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json

RUN npm ci --workspace apps/web

COPY apps/web ./apps/web

WORKDIR /repo/apps/web
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
