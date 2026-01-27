# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Copy the current directory contents into the container at /code
COPY . /code/app
COPY requirements.txt /code/

EXPOSE 8080
ENV PYTHONPATH=/code

WORKDIR /code
RUN pip install --no-cache-dir -r requirements.txt

CMD uvicorn app.main:app --port=${PORT:-8080} --host=0.0.0.0