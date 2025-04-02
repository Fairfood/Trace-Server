#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# pg_restore -U $POSTGRES_USER -d $POSTGRES_DB fabfile/db/devdb.sql

python manage.py migrate --settings=$DJANGO_SETTINGS_MODULE



# if [ "$DJANGO_SUPERUSER_USERNAME" ]
# then
#     echo "Creating super user $DJANGO_SUPERUSER_USERNAME"
#     python fairtrace_v2/manage.py createsuperuser \
#         --noinput \
#         --username $DJANGO_SUPERUSER_USERNAME \
#         --email $DJANGO_SUPERUSER_EMAIL
#     echo  "Created super user $DJANGO_SUPERUSER_USERNAME"
# fi

RUN neo4j-admin set-initial-password "${NEO4J_PASSWORD}" 2>/dev/null || true


$@

exec "$@"
