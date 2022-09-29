FROM python:3.10.5-buster

RUN mkdir container_src

COPY requirements.txt container_src/

COPY start.py container_src/

COPY config_files/ container_src/

WORKDIR /container_src

RUN pip install -r requirements.txt

RUN pip install recruiter-app==1.0.5

CMD ["python", "start.py"]

