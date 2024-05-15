# Используем официальный образ Node.js
FROM node:latest AS build

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы package.json и yarn.lock
COPY package.json yarn.lock ./

# Устанавливаем зависимости
RUN yarn install

# Копируем все остальные файлы приложения
COPY . .

ENV VITE_API_BASE_URL=http://vesna.tais.su:9000/api/v1
# Собираем приложение
RUN yarn build

# Отдельный этап для запуска приложения с использованием Nginx
FROM nginx:alpine

# Копируем собранное приложение из предыдущего этапа
COPY --from=build /app/dist /usr/share/nginx/html

# Копируем файл конфигурации nginx.conf с настройками порта
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт 8095 для nginx
EXPOSE 8095

# Команда запуска nginx внутри контейнера
CMD ["nginx", "-g", "daemon off;"]