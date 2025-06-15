#!/bin/sh
set -e

until python manage.py check --database default; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear

exec "$@"