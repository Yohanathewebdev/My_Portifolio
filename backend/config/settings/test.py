from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key-that-is-long-enough-for-django"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
INSTALLED_APPS += ["apps.test_models"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
