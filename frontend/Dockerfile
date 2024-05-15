# Используем официальный образ Node.js в качестве базы
FROM node:latest as build-stage

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы package.json и yarn.lock
COPY yarn.lock package*.json ./

# Устанавливаем зависимости
RUN yarn install

# Копируем остальные файлы в директорию приложения
COPY . .

# Собираем приложение
RUN yarn build

# Создаем production-ready образ Nginx
FROM nginx:latest

# Копируем собранные файлы из предыдущего этапа в директорию Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Переносим настройки Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Открываем порт 80
EXPOSE 80

# Команда для запуска Nginx внутри контейнера
CMD ["nginx", "-g", "daemon off;"]