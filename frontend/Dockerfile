FROM node:20-alpine AS base

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

FROM base AS development

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

FROM base AS build

ARG VITE_API_URL=http://localhost:8000
ARG VITE_API_AUTH_TOKEN=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_AUTH_TOKEN=$VITE_API_AUTH_TOKEN

RUN npm run build

FROM nginx:1.27-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
