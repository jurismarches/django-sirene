import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = 'secret_for_tests'
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_NAME"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": "postgresql",
        "PORT": "",
        "ATOMIC_REQUESTS": True,
    }
}
INSTALLED_APPS = ('django_sirene',)
MIDDLEWARE_CLASSES = ()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_sirene': {
            'handlers': ['console'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
        },
    },
}
