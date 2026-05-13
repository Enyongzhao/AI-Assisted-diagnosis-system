# Node 20 dev image for Vite + React
# --host flag makes Vite listen on 0.0.0.0 so Docker port mapping works
FROM node:20-alpine

WORKDIR /app

# Install deps first (cached layer — only re-runs when package.json changes)
COPY package*.json ./
RUN npm install

# Copy source (overridden by bind-mount in docker-compose dev mode)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "--port", "3000"]
