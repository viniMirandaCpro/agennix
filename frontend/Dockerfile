FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Em producao: npm run build && npm start
CMD ["npm", "run", "dev"]
