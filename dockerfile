FROM python:3.11

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi

COPY . .

#RUN chmod +x src/server.py
#ENTRYPOINT ["/bin/bash"] to debug
CMD ["python", "src/server.py"]