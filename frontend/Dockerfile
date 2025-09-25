FROM node:18-alpine

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./
# OR if using npm
# COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
