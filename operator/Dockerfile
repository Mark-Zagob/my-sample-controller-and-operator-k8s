FROM python:3.11
RUN apt update
RUN apt install git -y
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD [ "kopf","run","-A","./app.py"]