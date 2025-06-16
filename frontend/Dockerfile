# build env
FROM node:21.7.1-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build


FROM nginx:1.22.1

COPY --from=builder /app/build /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /app/static /app/media

EXPOSE 80