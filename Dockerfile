FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --ignore-scripts --no-audit --no-fund

COPY . .

ENV NETLIFY=true
ENV LOCAL_AUTH=true
ENV VITE_LOCAL_AUTH=true
ENV HOST=0.0.0.0
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
