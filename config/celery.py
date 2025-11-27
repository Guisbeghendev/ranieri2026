import os
from celery import Celery

# Define a variável de ambiente padrão para o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Cria a instância da aplicação Celery
# O nome 'config' deve ser o nome da pasta de configurações do seu projeto
app = Celery('config')

# Usa as configurações do Django
# O prefixo CELERY_* em settings.py será carregado
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobre tarefas em todos os apps instalados (como o 'repositorio')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Tarefa de exemplo para testar a funcionalidade básica do Celery."""
    print(f'Request: {self.request!r}')