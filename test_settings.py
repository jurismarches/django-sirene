import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = 'secret_for_tests'
DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
INSTALLED_APPS = ('django_sirene',)
MIDDLEWARE_CLASSES = ()
