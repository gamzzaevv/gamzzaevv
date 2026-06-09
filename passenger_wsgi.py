"""
Точка входа WSGI для виртуального хостинга reg.ru (Passenger).
Файл должен лежать в корне сайта: /www/mmastart.ru/passenger_wsgi.py
"""
import glob
import os
import site
import sys

# Корень проекта
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Подключаем виртуальное окружение (~/djangoenv или ~/venv)
home = os.path.expanduser("~")
for venv_name in ("djangoenv", "venv", ".venv"):
    pattern = os.path.join(home, venv_name, "lib", "python*", "site-packages")
    matches = glob.glob(pattern)
    if matches:
        site.addsitedir(matches[0])
        break

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.shared_hosting"

from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()
