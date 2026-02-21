FROM python:3.12.4-slim

# Устанавливаем uv
RUN pip install uv

# Создаем рабочую директорию
WORKDIR /app

# Сначала копируем только файлы, необходимые для установки зависимостей
COPY pyproject.toml .

# Устанавливаем зависимости напрямую (без виртуального окружения в контейнере)
RUN uv pip install --system .

# Копируем остальные файлы проекта
COPY . .

CMD alembic revision --autogenerate -m 'initial' && alembic upgrade head

CMD python src/main.py
