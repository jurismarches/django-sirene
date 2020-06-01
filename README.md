# django-sirene
[![CircleCI](https://circleci.com/gh/jurismarches/django-sirene.svg?style=svg)](https://circleci.com/gh/jurismarches/django-sirene)
[![codecov](https://codecov.io/gh/jurismarches/django-sirene/branch/master/graph/badge.svg)](https://codecov.io/gh/jurismarches/django-sirene)

Include [SIRENE](https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/)
database in your Django project.

All fields are not retrieved yet but why not add yours :).

## Usage

### Installation

```
pip install django-sirene
```

##### Settings

Add `django_sirene` to your installed apps.

These are settings you will want to redefine::

| Setting                            | Default | Details                                                 |
| ---------------------------------- | ------- | ------------------------------------------------------- |
| `DJANGO_SIRENE_LOCAL_PATH`         | `/tmp`  | define where files will be downloaded                   |

Make the migration
```
manage.py migrate django_sirene
```

### Populate database

```
manage.py populate_sirene_database
```
It will import the last 'stock' file then all next 'daily' files published.

You can see further option in the command help.
```
manage.py populate_sirene_database --help'
```

## Contributing

### Build, start docker container

```
cp .env.sample .env
docker-compose build
```

### Test django admin

Create superuser
```
docker-compose exec sirene example/manage.py createsuperuser
```

 Run django server
```
docker-compose exec sirene example/manage.py runserver 0:8000
```

### Run tests

```
docker-compose run --rm sirene make tests
```
