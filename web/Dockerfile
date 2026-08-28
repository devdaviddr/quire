FROM node:22-alpine

WORKDIR /srv

# Copy manifests first so the dependency layer is cached independently of source.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
