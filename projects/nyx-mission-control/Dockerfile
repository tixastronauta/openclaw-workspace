ARG BASE_IMAGE=node:24-alpine
FROM ${BASE_IMAGE}
WORKDIR /app
COPY package.json ./
COPY src ./src
COPY public ./public
ENV NODE_ENV=production
ENV PORT=4317
EXPOSE 4317
CMD ["npm", "start"]
