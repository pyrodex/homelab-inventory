FROM node:22-alpine as build

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code and config files
COPY index.html ./
COPY vite.config.js ./
COPY tailwind.config.cjs ./
COPY postcss.config.cjs ./
COPY src ./src

# Build the application (outputs to /app/dist)
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Create non-root user/group with UID/GID 1000
RUN addgroup -g 1000 app && adduser -D -u 1000 -G app app

# Copy built files to nginx (Vite builds to dist/)
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ensure nginx runtime dirs are writable by non-root user
RUN mkdir -p /var/cache/nginx /var/run /var/log/nginx && \
    chown -R app:app /var/cache/nginx /var/run /var/log/nginx

EXPOSE 8080

USER app
CMD ["nginx", "-g", "daemon off;"]
