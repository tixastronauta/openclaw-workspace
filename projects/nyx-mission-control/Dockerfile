FROM node:24-alpine
WORKDIR /app
COPY package.json ./
COPY src ./src
COPY public ./public
ENV NODE_ENV=production
ENV PORT=4317
EXPOSE 4317
CMD ["npm", "start"]
