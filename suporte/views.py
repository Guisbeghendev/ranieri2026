from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from .models import Topico, MensagemSuporte, TopicoStatus
# Importe o NOVO formulário
from .forms import TopicoCreateForm, MensagemSuporteForm, TopicoStatusForm
from users.models import CustomUser  # Assumindo que seu CustomUser está em users.models
from .admin import grupo_suporte


# ==============================================================================
# 0. MIXIN DE SEGURANÇA (Autorização)
# ==============================================================================

class TopicoSecurityMixin(UserPassesTestMixin):
    """
    Garante que apenas o criador do tópico OU um membro da Equipe de Suporte
    possa acessar o Tópico.
    """

    def test_func(self):
        topico = self.get_object()
        user = self.request.user

        # 1. Usuário é o criador?
        if topico.criador == user:
            return True

        # 2. Usuário é da Equipe de Suporte ou Staff/Superuser?
        if user.is_staff or user.groups.filter(name=grupo_suporte).exists():
            return True

        return False

    def handle_no_permission(self):
        messages.error(self.request, _("Você não tem permissão para acessar este tópico."))
        return redirect('suporte:topico_list')


# NOVO: MIXIN para garantir acesso apenas para Staff/Superuser
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Garante que apenas usuários Staff ou Superuser acessem a view."""

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser or user.groups.filter(name=grupo_suporte).exists()

    def handle_no_permission(self):
        messages.error(self.request, _("Você não tem permissão para realizar esta ação."))
        return redirect('suporte:topico_list')


# ==============================================================================
# 1. LISTAGEM DE TÓPICOS (USER/FRONT-END)
# ==============================================================================

class TopicoListView(LoginRequiredMixin, ListView):
    # ... (Conteúdo da TopicoListView permanece inalterado) ...
    """Exibe todos os tópicos criados pelo usuário logado (usuário comum) ou
    TODOS os tópicos (equipe de suporte)."""
    model = Topico
    template_name = 'suporte/topico_list.html'
    context_object_name = 'topicos'

    def get_queryset(self):
        """
        CORREÇÃO: Implementa o filtro condicional:
        - Equipe de Suporte: Vê TODOS os tópicos.
        - Usuário Comum: Vê APENAS os seus tópicos.
        """
        user = self.request.user

        # Verifica se o usuário é da equipe de suporte
        is_suporte_equipe = user.is_staff or user.groups.filter(name=grupo_suporte).exists()

        if is_suporte_equipe:
            # Equipe de suporte (Admin, Staff) vê TODOS os tópicos
            queryset = Topico.objects.all().order_by('-atualizado_em')
        else:
            # Usuário comum vê APENAS os seus tópicos
            queryset = Topico.objects.filter(criador=user).order_by('-atualizado_em')

        # Lógica de Notificação: Se o último autor da mensagem não foi o usuário,
        # e o status não for Resolvido/Fechado, o tópico pode ter uma nova resposta.
        for topico in queryset:
            ultima_mensagem = topico.mensagens.last()

            # Se a última mensagem existir e não for do próprio criador:
            if ultima_mensagem and ultima_mensagem.autor != self.request.user:
                # E o status sugere que a bola está com o usuário
                if topico.status in [TopicoStatus.EM_ATENDIMENTO, TopicoStatus.AGUARDANDO_INFO]:
                    # Lógica para usuários comuns: nova resposta se veio do suporte
                    if not is_suporte_equipe and (ultima_mensagem.autor.is_staff or ultima_mensagem.autor.groups.filter(
                            name=grupo_suporte).exists()):
                        topico.tem_nova_resposta = True
                    # Lógica para equipe de suporte: nova resposta se veio do usuário comum
                    elif is_suporte_equipe and (
                            topico.status == TopicoStatus.NOVO or topico.status == TopicoStatus.AGUARDANDO_INFO) and ultima_mensagem.autor == topico.criador:
                        topico.tem_nova_resposta = True
                    else:
                        topico.tem_nova_resposta = False
                else:
                    topico.tem_nova_resposta = False
            else:
                topico.tem_nova_resposta = False

        return queryset


# ==============================================================================
# 2. CRIAÇÃO DE TÓPICO
# ==============================================================================

class TopicoCreateView(LoginRequiredMixin, CreateView):
    # ... (Conteúdo da TopicoCreateView permanece inalterado) ...
    """Permite ao usuário logado criar um novo tópico de suporte."""
    model = Topico
    form_class = TopicoCreateForm
    template_name = 'suporte/topico_create.html'

    def form_valid(self, form):
        """Define o criador e o status inicial antes de salvar."""
        topico = form.save(commit=False)
        topico.criador = self.request.user
        topico.status = TopicoStatus.NOVO
        topico.save()

        messages.success(self.request,
                         _(f"O tópico '{topico.assunto}' foi criado com sucesso. Nossa equipe responderá em breve."))
        return HttpResponseRedirect(topico.get_absolute_url())

    def get_success_url(self):
        # A URL de sucesso é definida no form_valid, mas esta é a garantia
        return reverse_lazy('suporte:topico_list')


# ==============================================================================
# 3. DETALHE DO TÓPICO E RESPOSTA (Usuário e Admin)
# ==============================================================================

class TopicoDetailView(LoginRequiredMixin, TopicoSecurityMixin, DetailView):
    """Exibe os detalhes de um tópico e suas mensagens."""
    model = Topico
    template_name = 'suporte/topico_detail.html'
    context_object_name = 'topico'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # O formulário de resposta sempre estará disponível no detalhe
        context['form'] = MensagemSuporteForm()

        # Filtra e ordena as mensagens para exibição
        context['mensagens'] = self.object.mensagens.all().select_related('autor')

        # Verifica se o usuário é da equipe de suporte para exibir opções adicionais, se necessário
        is_suporte_equipe = self.request.user.is_staff or self.request.user.groups.filter(
            name=grupo_suporte).exists()
        context['is_suporte_equipe'] = is_suporte_equipe

        # NOVO: Injeta o formulário de status APENAS para a equipe de suporte
        if is_suporte_equipe:
            # O formulário é inicializado com a instância atual do tópico
            context['status_form'] = TopicoStatusForm(instance=self.object)

        return context


# A View de resposta é separada para lidar com o POST do formulário de mensagem
class MensagemSuporteCreateView(LoginRequiredMixin, TopicoSecurityMixin, View):
    # ... (Conteúdo da MensagemSuporteCreateView permanece inalterado) ...
    """Lida com a submissão de novas mensagens (respostas) em um tópico existente."""

    # Reimplementa get_object para que o TopicoSecurityMixin funcione
    def get_object(self):
        return get_object_or_404(Topico, pk=self.kwargs['pk'])

    def post(self, request, pk):
        topico = self.get_object()

        form = MensagemSuporteForm(request.POST)

        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.topico = topico
            mensagem.autor = request.user
            mensagem.save()

            # --- LÓGICA DE ATUALIZAÇÃO DO STATUS DO TÓPICO ---
            is_suporte = request.user.is_staff or request.user.groups.filter(name=grupo_suporte).exists()

            # 1. Se quem respondeu é o Criador (Usuário Comum):
            if request.user == topico.criador:
                # Se o status era 'Aguardando Info' (Admin esperando), volta para 'Em Atendimento'
                if topico.status == TopicoStatus.AGUARDANDO_INFO:
                    topico.status = TopicoStatus.EM_ATENDIMENTO
                # Se estava Novo/Resolvido/Fechado, e o criador respondeu, reabre/muda para 'Em Atendimento'
                elif topico.status in [TopicoStatus.NOVO, TopicoStatus.RESOLVIDO, TopicoStatus.FECHADO]:
                    topico.status = TopicoStatus.EM_ATENDIMENTO

            # 2. Se quem respondeu é o Admin/Suporte:
            elif is_suporte:
                # Se o status era Novo ou Fechado/Resolvido, muda para 'Em Atendimento'
                if topico.status in [TopicoStatus.NOVO, TopicoStatus.RESOLVIDO, TopicoStatus.FECHADO]:
                    topico.status = TopicoStatus.EM_ATENDIMENTO

            topico.save()

            messages.success(request, _("Mensagem enviada com sucesso."))

        else:
            messages.error(request, _("Houve um erro ao enviar a mensagem."))

        # Redireciona de volta para a tela de detalhes do tópico
        return HttpResponseRedirect(topico.get_absolute_url())

    def get(self, request, pk):
        # Evita que a URL de POST seja acessada via GET
        return redirect('suporte:topico_detail', pk=pk)


# NOVO: View para atualizar o Status e Responsável do Tópico (Staff/Superuser)
class TopicoStatusUpdateView(StaffRequiredMixin, View):
    """Lida com a submissão do formulário de atualização de status e responsável."""

    def get_object(self):
        # Obtém o tópico com base no PK da URL
        return get_object_or_404(Topico, pk=self.kwargs['pk'])

    def post(self, request, pk):
        topico = self.get_object()

        # Inicializa o formulário com a instância e os dados POST
        form = TopicoStatusForm(request.POST, instance=topico)

        if form.is_valid():
            # A lógica de fluxo de trabalho (mudar de NOVO para ATND) está no form.save()
            form.save()

            messages.success(request, _("Status e/ou Responsável do tópico atualizados com sucesso."))
        else:
            # Se o formulário for inválido (ex: erro de clean_status), exibe a mensagem de erro.
            # No caso de erro, é melhor redirecionar para o detalhe e exibir os erros.
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")

        return HttpResponseRedirect(topico.get_absolute_url())

    def get(self, request, pk):
        # Redireciona para evitar acesso GET à URL de POST
        return redirect('suporte:topico_detail', pk=pk)


# ==============================================================================
# 4. FECHAMENTO DO TÓPICO
# ==============================================================================

class TopicoCloseView(LoginRequiredMixin, TopicoSecurityMixin, View):
    # ... (Conteúdo da TopicoCloseView permanece inalterado) ...
    """Permite fechar um tópico, alterando o status para TopicoStatus.FECHADO."""

    # Reimplementa get_object para que o TopicoSecurityMixin funcione
    def get_object(self):
        return get_object_or_404(Topico, pk=self.kwargs['pk'])

    def post(self, request, pk):
        topico = self.get_object()

        # A checagem de permissão é feita pelo TopicoSecurityMixin no dispatch.

        if topico.status == TopicoStatus.FECHADO:
            messages.warning(request, _("Este tópico já está fechado."))
            return HttpResponseRedirect(topico.get_absolute_url())

        topico.status = TopicoStatus.FECHADO
        topico.save()

        messages.success(request, _("Tópico fechado com sucesso."))
        return HttpResponseRedirect(topico.get_absolute_url())

    def get(self, request, pk):
        # Redireciona para evitar acesso GET à URL de fechamento
        return redirect('suporte:topico_detail', pk=pk)