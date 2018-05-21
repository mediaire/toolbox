FROM python:3.5-alpine

COPY requirements.txt /src/requirements.txt

WORKDIR /src
RUN pip install -r requirements.txt

COPY . /src

RUN python setup.py install

