from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria automaticamente um Profile quando um novo CustomUser é criado.
    Salva o Profile em edições subsequentes do CustomUser.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        # Salva o Profile se o CustomUser estiver sendo editado e o Profile já existir.
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            # Não tenta criar. Tentar criar um Profile aqui causa a violação de chave
            # (users_profile_user_id_key) quando a transação falha no views.py,
            # pois o CustomUser já foi salvo em memória.
            pass