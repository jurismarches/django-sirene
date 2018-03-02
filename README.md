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
| `DJANGO_SIRENE_DAYS_TO_KEEP_FILES` | `30`    | define how many days you want to keep downloaded files  |

Make the migration
```
manage.py migrate django_sirene
```

### Populate database

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

Create superuser
```
example/manage.py createsuperuser
```

 Run django server
```
example/manage.py runserver 0:8000
```

### Run tests

```
make tests
```
