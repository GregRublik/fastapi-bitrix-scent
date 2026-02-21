import os
import sys

sys.path.append(os.path.dirname(__file__))

import os

INTERP = os.path.expanduser("/var/www/u2842936/data/venv/bin/python")
# INTERP = os.path.expanduser("/var/www/u2842936/data/www/sporbita-developers.ru/.venv/bin/python")

if sys.executable != INTERP:
   os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from src.main import application # noqa
