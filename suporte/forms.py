from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import Topico, MensagemSuporte, TopicoStatus  # Importe TopicoStatus

# Importa o modelo de usuário do seu projeto
User = get_user_model()


# ==============================================================================
# 1. FORMULÁRIO PARA CRIAÇÃO DE TÓPICO (Usuário Comum)
# ==============================================================================

class TopicoCreateForm(forms.ModelForm):
    """
    Formulário usado pelo CustomUser para iniciar um novo tópico de suporte.
    """

    # O campo 'assunto' é o único que o usuário precisa preencher diretamente.
    class Meta:
        model = Topico
        fields = ['assunto']
        labels = {
            'assunto': _('Assunto da Solicitação'),
        }
        widgets = {
            'assunto': forms.TextInput(attrs={'placeholder': _('Ex: Problema de login, erro no perfil, etc.')})
        }

    # Sobrescreve init para, opcionalmente, adicionar mais campos ou classes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona uma classe CSS padrão do Django Admin para o campo 'assunto'
        self.fields['assunto'].widget.attrs.update({'class': 'vTextField'})


# ==============================================================================
# 2. FORMULÁRIO PARA RESPOSTA (Usuário ou Admin)
# ==============================================================================

class MensagemSuporteForm(forms.ModelForm):
    """
    Formulário usado para adicionar uma nova mensagem a um tópico existente.
    """

    # O campo 'conteudo' é o único que o usuário preenche.
    class Meta:
        model = MensagemSuporte
        fields = ['conteudo']
        labels = {
            'conteudo': _('Sua Mensagem'),
        }
        widgets = {
            'conteudo': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Digite sua resposta ou detalhes adicionais aqui...'),
            })
        }

    # Sobrescreve init para, opcionalmente, adicionar classes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conteudo'].widget.attrs.update({'class': 'vLargeTextField'})


# ==============================================================================
# 3. NOVO: FORMULÁRIO DE ATUALIZAÇÃO DE STATUS (Staff/Superuser)
# ==============================================================================

class TopicoStatusForm(forms.ModelForm):
    """
    Formulário usado exclusivamente por Staff/Superuser para ajustar o
    status e o responsável do Tópico diretamente no frontend.
    """

    # Limita o campo admin_responsavel apenas a usuários staff
    admin_responsavel = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True).order_by('username'),
        required=False,
        label=_("Responsável (Admin/Staff)"),
        empty_label=_("Nenhum (Novo/Aguardando Atribuição)"),
        widget=forms.Select(attrs={'class': 'vSelect'})
    )

    class Meta:
        model = Topico
        fields = ['status', 'admin_responsavel']
        labels = {
            'status': _('Status do Chamado'),
        }
        widgets = {
            'status': forms.Select(attrs={'class': 'vSelect'})
        }

    def clean_status(self):
        """Impede que o status seja alterado para NOVO manualmente, respeitando a lógica do Admin."""
        status = self.cleaned_data.get('status')
        # Apenas permite que o status seja alterado para NOVO se o tópico ainda não tiver sido salvo.
        # No entanto, em um formulário de edição, o status 'NOVO' não deve ser selecionável.
        # Usamos uma checagem mais suave para evitar erros comuns no frontend.
        if self.instance and status == TopicoStatus.NOVO and self.instance.status != TopicoStatus.NOVO:
            raise forms.ValidationError(_("O status 'Novo' só pode ser definido na criação."))

        # Garante que o usuário Staff não possa setar FECHADO e RESOLVIDO ao mesmo tempo que responde (se fosse o caso)
        if status in [TopicoStatus.FECHADO, TopicoStatus.RESOLVIDO] and self.instance.status not in [
            TopicoStatus.FECHADO, TopicoStatus.RESOLVIDO]:
            # Adiciona uma confirmação sutil, se desejar, mas a View deve lidar com a ação.
            pass

        return status

    def save(self, commit=True):
        """Sobrescreve save para replicar a lógica de fluxo de trabalho do admin."""
        topico = super().save(commit=False)

        # Lógica de fluxo de trabalho (replicada do admin.py):
        # Se um responsável foi atribuído E o status atual era Novo, muda para Em Atendimento.
        if topico.admin_responsavel and topico.status == TopicoStatus.NOVO:
            topico.status = TopicoStatus.EM_ATENDIMENTO

        if commit:
            topico.save()
        return topico