from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = _("Gerenciamento de Usuários e Registros")

    def ready(self):
        # Importa os sinais para garantir que eles sejam conectados
        # quando o Django for iniciado.
        import users.signals