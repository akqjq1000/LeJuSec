# LeJuSec 웹 콘솔(운영자 GUI) 컨테이너 이미지.
# 빌드 컨텍스트: web/
# 1단계: Vite 정적 빌드 → 2단계: nginx 정적 서빙
FROM node:20-alpine AS build

WORKDIR /app

# 브라우저가 호출할 컨트롤 플레인 주소(빌드 타임 주입). 기본은 호스트에 퍼블리시된 API.
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
