from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Usuários e Perfis'

    def ready(self):
        """
        Importa os sinais para que sejam conectados (hooked up) quando o Django iniciar.
        """
        import users.signals