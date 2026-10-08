Foodgram
Описание
Foodgram — это онлайн-сервис для публикации рецептов, где пользователи могут публиковать собственные блюда, добавлять чужие рецепты в избранное, оформлять подписки на авторов, а также составлять и скачивать сводный список покупок.

Ссылка на запущенный проект
Проект развернут и доступен по адресу:
https://foodgram.myftp.org

Используемые технологии
Бэкенд: Python, Django, Django REST Framework, Gunicorn

База данных: PostgreSQL

Фронтенд: Vue.js

Инфраструктура: Docker, Docker Compose, Nginx, GitHub Actions

Локальный запуск с помощью Docker
Клонируйте репозиторий:

Bash
git clone https://github.com/iRlyLovePumpkins/foodgram.git
cd foodgram
Создайте и заполните файл .env в корневом каталоге проекта.

Соберите и запустите контейнеры:

Bash
docker compose up --build -d
Выполните миграции и соберите статические файлы:

Bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic --no-input

Tests: docker exec -it foodgram-backend-1 pytest ../tests

Автор: Александра
GitHub: iRlyLovePumpkins
