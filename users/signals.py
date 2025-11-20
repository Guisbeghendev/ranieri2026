from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria automaticamente um Profile quando um novo CustomUser é criado.
    """
    if created:
        Profile.objects.create(user=instance)
    # O bloco 'else' anterior, que continha 'instance.profile.save()',
    # foi removido para evitar a recursão infinita (loop) no salvamento.