from django.apps import AppConfig

class RepositorioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repositorio'

    def ready(self):
        # Importa os sinais quando o app estiver pronto
        import repositorio.signals