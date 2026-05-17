# Multi-stage build for React frontend
FROM node:18-alpine as builder
WORKDIR /app
ENV CI=true
COPY package*.json ./
# If you have yarn.lock or pnpm-lock, copy those too
COPY .yarn .yarn
RUN npm ci --silent
COPY . .
RUN npm run build

# Nginx stage
FROM nginx:stable-alpine as web
COPY --from=builder /app/build /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
