# pull official base image
FROM python:3.8.3-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt-get update
RUN apt-get install -y git
RUN apt-get install -y postgresql
RUN apt-get install -y libxslt-dev
RUN apt-get install -y libxml2-dev
RUN apt-get install -y libc-dev
RUN apt-get install -y musl-dev
RUN apt-get install -y libffi-dev
RUN apt-get install -y libssl-dev
RUN apt -y install libjpeg-dev
RUN apt -y install libjpeg-dev zlib1g zlib1g-dev
RUN apt-get -y install python-pil python3-pil
RUN apt-get install -y zlib1g
RUN apt-get install -y gcc python3-dev
RUN apt-get install -y libgeos++-dev
RUN apt-get install -y postgresql-client
RUN apt-get install -y libpq-dev

# install dependencies
RUN python3 -m pip install pip==19.3.1
RUN mkdir req
COPY ./requirements/* req
RUN python3 -m pip install -r req/local.txt

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# copy project
COPY . .

# run entrypoint.sh
#RUN ["chmod", "+x", "/usr/src/app/entrypoint.sh"]
#ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
