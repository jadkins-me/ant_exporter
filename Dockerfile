FROM python:3.10-slim

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -y --no-install-recommends bash

RUN pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt ./

COPY . .

ENV PATH="/usr/src/app/.local/bin:${PATH}"

RUN pip install --no-cache-dir -r requirements.txt

ENV HOST=0.0.0.0
ENV LISTEN=8080
ENV CONFIG_FILE=./config.yml

# Run the main.py script
CMD ["python", "src/main.py"]