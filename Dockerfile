# Use the official Python image as the base image
FROM python:3.11

RUN apt-get update && apt-get install -y wget
RUN wget https://github.com/jwilder/dockerize/releases/download/v0.7.0/dockerize-linux-amd64-v0.7.0.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-v0.7.0.tar.gz \
    && rm dockerize-linux-amd64-v0.7.0.tar.gz

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN sed -i 's/\r$//' run.sh

EXPOSE 5000

CMD ["dockerize", "-wait", "tcp://postgres:5432", "-timeout", "30s", "bash", "run.sh"]
