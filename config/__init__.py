# Este arquivo garante que o app Celery seja importado quando o Django iniciar,
# para que as tarefas possam ser reconhecidas.
from .celery import app as celery_app

__all__ = ('celery_app',)