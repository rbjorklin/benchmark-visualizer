FROM python:3-buster

RUN pip install --compile pandas psycopg2
COPY parser.py ./

ENTRYPOINT ["/parser.py"]
