from __future__ import annotations

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

import config.urls as urlconf  # noqa: E402
from apps.core.scoping import check_authentication_urlconf  # noqa: E402

violations = check_authentication_urlconf(urlconf)
if violations:
    for violation in violations:
        print(violation)
    raise SystemExit(1)
print("Authentication access gate passed.")
