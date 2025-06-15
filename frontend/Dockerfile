# build env
FROM node:21.7.1-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build
# CMD cp -r build result_build

FROM nginx:1.22.1

# WORKDIR /nginx

COPY --from=builder /app/build /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
# COPY --from=builder /app/build/index.html /nginx/index.html
# COPY --from=builder /app/build/static /nginx/static
# COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80