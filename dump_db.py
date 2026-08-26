import os
import django
import subprocess

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navoke_backend.settings')
django.setup()

from django.conf import settings

db = settings.DATABASES['default']
dump_command = f"pg_dump -U {db['USER']} -h {db['HOST']} -p {db['PORT']} -d {db['NAME']} > dump.sql"
print(f"Выполняю: {dump_command}")
subprocess.run(dump_command, shell=True)
print("Дамп создан: dump.sql")