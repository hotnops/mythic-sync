FROM python:3.8.5-alpine3.12

COPY requirements.txt .
COPY sync.py .
RUN pip install -r requirements.txt
CMD python sync.py
