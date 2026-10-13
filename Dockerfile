FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --ignore-scripts --no-audit --no-fund

COPY . .

ENV HOST=0.0.0.0
ENV CHOKIDAR_USEPOLLING=true
EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
