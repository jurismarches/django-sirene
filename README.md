# django-sirene


Include [SIRENE](https://www.sirene.fr/sirene/public/accueil) database in your
Django project.

## Usage

### Installation

```
pip install django-sirene
```

Add `django_sirene` to your installed apps.

Make the migration
```
manage.py migrate django_sirene
```

### Populate database

```
manage.py populate_sirene_database
```
It will import the last 'stock' file then all next 'daily' files published.

You can populate database at a past date with `at` parameter.
```
manage.py populate_sirene_database --at '2017-11-30'
```

## Contributing

### Build, start and attach to docker container

```
docker-compose up -d
docker exec -ti CONTAINER_ID bash
```

### Test django admin

#### Create superuser
```
example/manage.py createsuperuser

```

#### Run django server

```
example/manage.py runserver 0:8000
```

### Run tests

```
DJANGO_SETTINGS_MODULE=test_settings django-admin test django_sirene.tests
```
