FROM python:3
WORKDIR /app
COPY requirements.txt /app/
RUN  pip install -r requirements.txt
COPY circle_dj_pg_demo /app/circle_dj_pg_demo
