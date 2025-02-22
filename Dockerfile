FROM python:3.10.1

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

#RUN alembic downgrade -1 #удалить миграцию

#RUN alembic revision --autogenerate ## создать миграции

#RUN alembic upgrade head ##Применить миграции

CMD ["python", "main.py"]
