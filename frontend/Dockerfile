FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Expose port for Next.js
EXPOSE 3000

# Start Next.js in development mode for hot reloading
CMD ["npm", "run", "dev"]
