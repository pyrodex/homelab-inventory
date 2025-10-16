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

# Copy built files to nginx (Vite builds to dist/)
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
