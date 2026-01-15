import os
from celery import Celery

# 1. Define o módulo de configurações padrão do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# 2. Namespace 'CELERY' garante que as configurações em settings.py sejam lidas corretamente
# Ex: CELERY_BROKER_URL vira broker_url internamente.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3. Auto-descobre tasks.py em todos os apps instalados (como o galerias/tasks.py)
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')