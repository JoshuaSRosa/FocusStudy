FROM postgres:16-alpine

# Variables can be overridden by docker-compose.yml
ENV POSTGRES_DB=database
ENV POSTGRES_USER=admin
ENV POSTGRES_PASSWORD=changeme
ENV LANG=pt_BR.UTF-8

COPY init.sql /docker-entrypoint-initdb.d/01-init.sql

EXPOSE 5432