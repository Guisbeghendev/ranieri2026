import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Namespace 'CELERY' garante que as configurações em settings.py sejam lidas corretamente
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobre tasks.py em todos os apps instalados
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')