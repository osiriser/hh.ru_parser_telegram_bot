FROM python:3.7
RUN apt-get update
RUN python3 -m pip install --upgrade pip
RUN apt-get install -y chromium
RUN apt-get install -y chromium-driver
WORKDIR /app
COPY requirements/requirements.txt /app
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . .
LABEL author="mv_rogozov"
ENV TG_TOKEN=xxxxxxxxxx
EXPOSE 8081/tcp 8082/tcp
CMD ["python3", "job_parser.py"]