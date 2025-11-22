from django.apps import AppConfig

class MensagensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mensagens'
    verbose_name = "Comunicação e Chat"

    def ready(self):
        """
        Importa o módulo signals para que os decoradores @receiver sejam registrados.
        """
        # AQUI VOCÊ IMPORTA SEU ARQUIVO signals.py
        import mensagens.signals