# ---- Stage 1: build ----
FROM node:20-slim AS builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY index.html .
COPY vite.config.js .
COPY src/ ./src/

RUN npm run build


# ---- Stage 2: produccion ----
FROM nginx:alpine

# Eliminar configuracion default de nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copiar configuracion personalizada
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copiar el build de Vite
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
