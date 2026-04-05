FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
COPY next.config.ts tsconfig.json ./
COPY public ./public
COPY src ./src
RUN npm ci --silent
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start", "--", "-p", "3000"]
