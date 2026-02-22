import os
import sys

# путь к корню проекта
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# добавляем корень проекта в sys.path
sys.path.insert(0, PROJECT_ROOT)

INTERP = os.path.expanduser("/var/www/u2842936/data/venv/bin/python")
# INTERP = os.path.expanduser("/var/www/u2842936/data/www/sporbita-developers.ru/.venv/bin/python")

if sys.executable != INTERP:
   os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from src.main import application # noqa
