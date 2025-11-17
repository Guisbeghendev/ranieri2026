from django.db import models
from django.contrib.auth.models import AbstractUser, Group as AuthGroup
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import signals
from django.db.models.signals import post_save
from django.dispatch import receiver


# ==============================================================================
# CHOICES E ENUMS DO PROJETO
# ==============================================================================

class CustomUserTipo(models.TextChoices):
    """Tipos de usuários que podem fazer login no sistema."""
    ADMIN = 'ADMIN', _('Administrador')
    ALUNO = 'ALUNO', _('Aluno')
    PROFESSOR = 'PROFESSOR', _('Professor')
    COLABORADOR = 'COLABORADOR', _('Colaborador')
    RESPONSAVEL = 'RESPONSAVEL', _('Responsável')
    URE = 'URE', _('URE (Unidade Regional de Ensino)')
    OUTRO_VISITANTE = 'OUTRO_VISITANTE', _('Outros Visitantes')


class TipoProfessor(models.TextChoices):
    """Papéis específicos dentro da categoria Professor."""
    REGENTE = 'REGENTE', _('Regente')
    COLABORATIVO = 'COLABORATIVO', _('Colaborativo')
    ED_FISICA = 'ED_FISICA', _('Ed. Física')
    ARTES = 'ARTES', _('Artes')
    CULTURA_MOV = 'CULTURA_MOV', _('Cultura do Movimento')
    TUTOR = 'TUTOR', _('Tutor')
    ORIENT_ESTUDOS = 'ORIENT_ESTUDOS', _('Orientação de Estudos')
    TUTORIA = 'TUTORIA', _('Tutoria')
    INGLES = 'INGLES', _('Inglês')
    SALA_LEITURA = 'SALA_LEITURA', _('Sala de Leitura')
    PROATI = 'PROATI', _('Proati')
    ESTAGIO = 'ESTAGIO', _('Estágio')
    OUTROS = 'OUTROS', _('Outros')


class FuncaoColaborador(models.TextChoices):
    """Funções específicas dentro da categoria Colaborador."""
    DIRECAO = 'DIRECAO', _('Direção')
    VICE_DIR = 'VICE_DIR', _('Vice Direção')
    COORD_PED = 'COORD_PED', _('Coordenação Pedagógica')
    SECRETARIA = 'SECRETARIA', _('Secretaria')
    AGENTE_ESCOLAR = 'AGENTE_ESCOLAR', _('Agente de Org./Ser. Escolar (QSE)')
    PROATI = 'PROATI', _('Proati')
    MERENDA = 'MERENDA', _('Merenda')
    LIMPEZA = 'LIMPEZA', _('Limpeza')
    ESTAGIO = 'ESTAGIO', _('Estágio')
    OUTRO = 'OUTRO', _('Outro')


class TipoGrupo(models.TextChoices):
    """Contextos para os Grupos de Audiência."""
    TURMA = 'TURMA', _('Turma Escolar (Ex: 3A-2025)')
    SETOR = 'SETOR', _('Setor/Corpo Docente (Ex: Coordenação)')
    PROJETO = 'PROJETO', _('Projeto/Adicional (Criação Restrita)')


# ==============================================================================
# 1. ENTIDADES DE REGISTRO (Base de Dados da Escola)
# ==============================================================================

class RegistroBase(models.Model):
    """Modelo abstrato que unifica os campos comuns de identificação."""

    nome_completo = models.CharField(
        max_length=255,
        verbose_name=_("Nome Completo")
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.nome_completo


class Turma(models.Model):
    """A espinha dorsal da organização pedagógica."""
    nome = models.CharField(
        max_length=50,
        verbose_name=_("Nome da Turma (Ex: 3º A)")
    )
    ano_letivo = models.IntegerField(
        verbose_name=_("Ano Letivo")
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name=_("Turma Ativa")
    )

    class Meta:
        verbose_name = _("Turma")
        verbose_name_plural = _("Turmas")
        unique_together = ('nome', 'ano_letivo')

    def __str__(self):
        return f"{self.nome} ({self.ano_letivo})"


class RegistroProfessor(RegistroBase):
    """Lista e define o papel oficial dos docentes."""
    tipo_professor = models.CharField(
        max_length=20,
        choices=TipoProfessor.choices,
        default=TipoProfessor.OUTROS,
        verbose_name=_("Tipo de Professor")
    )
    turmas = models.ManyToManyField(
        Turma,
        blank=True,
        related_name='professores_adicionais',
        verbose_name=_("Turmas Adicionais")
    )

    class Meta:
        verbose_name = _("Registro de Professor")
        verbose_name_plural = _("Registros de Professores")

    def __str__(self):
        return f"{self.nome_completo} - {self.get_tipo_professor_display()}"


Turma.add_to_class('professor_regente', models.ForeignKey(
    RegistroProfessor,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='turmas_regidas',
    verbose_name=_("Professor Regente")
))


def validate_regente_type(sender, instance, **kwargs):
    if instance.professor_regente and instance.professor_regente.tipo_professor != TipoProfessor.REGENTE:
        raise ValidationError(
            _('O professor regente deve ter o tipo de professor definido como "Regente".')
        )


signals.pre_save.connect(validate_regente_type, sender=Turma)


class RegistroAluno(RegistroBase):
    """Dados de identificação oficiais dos alunos."""
    ra_numero = models.CharField(
        max_length=20,
        verbose_name=_("RA (Registro do Aluno) - Número")
    )
    ra_digito_verificador = models.CharField(
        max_length=2,
        verbose_name=_("RA - Dígito Verificador")
    )
    turma = models.ForeignKey(
        Turma,
        on_delete=models.PROTECT,
        related_name='alunos',
        verbose_name=_("Turma")
    )

    class Meta:
        verbose_name = _("Registro de Aluno")
        verbose_name_plural = _("Registros de Alunos")
        unique_together = ('ra_numero', 'ra_digito_verificador', 'turma')

    def __str__(self):
        return f"{self.nome_completo} (RA: {self.ra_numero}-{self.ra_digito_verificador})"


class RegistroColaborador(RegistroBase):
    """Dados da equipe não-docente."""
    matricula_ou_identificador = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Matrícula ou Identificador")
    )
    funcao = models.CharField(
        max_length=20,
        choices=FuncaoColaborador.choices,
        default=FuncaoColaborador.OUTRO,
        verbose_name=_("Função no Colégio")
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name=_("Colaborador Ativo")
    )

    class Meta:
        verbose_name = _("Registro de Colaborador")
        verbose_name_plural = _("Registros de Colaboradores")

    def __str__(self):
        return f"{self.nome_completo} - {self.get_funcao_display()}"


class RegistroResponsavel(RegistroBase):
    """Registro de pais ou responsáveis."""
    alunos = models.ManyToManyField(
        RegistroAluno,
        related_name='responsaveis',
        verbose_name=_("Alunos Dependentes")
    )

    class Meta:
        verbose_name = _("Registro de Responsável")
        verbose_name_plural = _("Registros de Responsáveis")

    def __str__(self):
        return self.nome_completo


class RegistroURE(RegistroBase):
    """Perfis de Unidade Regional de Ensino (URE)."""
    funcao = models.CharField(
        max_length=100,
        verbose_name=_("Função ou Cargo na URE")
    )

    class Meta:
        verbose_name = _("Registro URE")
        verbose_name_plural = _("Registros URE")

    def __str__(self):
        return f"{self.nome_completo} ({self.funcao})"


class RegistroOutrosVisitantes(RegistroBase):
    """Perfis de outros visitantes que necessitam de login."""
    descricao = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Descrição do Vínculo")
    )

    class Meta:
        verbose_name = _("Registro de Outro Visitante")
        verbose_name_plural = _("Registros de Outros Visitantes")

    def __str__(self):
        return self.nome_completo


# ==============================================================================
# 2. CUSTOMUSER (Hub de Login e Autenticação)
# ==============================================================================

class CustomUser(AbstractUser):
    tipo_usuario = models.CharField(
        max_length=20,
        choices=CustomUserTipo.choices,
        default=CustomUserTipo.ALUNO,
        verbose_name=_("Tipo de Usuário")
    )

    is_fotografo = models.BooleanField(
        default=False,
        verbose_name=_("Pode gerenciar suas próprias galerias")
    )
    is_fotografo_master = models.BooleanField(
        default=False,
        verbose_name=_("Pode gerenciar todas as galerias")
    )

    registro_aluno = models.OneToOneField(
        RegistroAluno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de Aluno")
    )
    registro_professor = models.OneToOneField(
        RegistroProfessor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de Professor")
    )
    registro_colaborador = models.OneToOneField(
        RegistroColaborador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de Colaborador")
    )
    registro_responsavel = models.OneToOneField(
        RegistroResponsavel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de Responsável")
    )
    registro_ure = models.OneToOneField(
        RegistroURE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de URE")
    )
    registro_visitante = models.OneToOneField(
        RegistroOutrosVisitantes,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name=_("Vínculo de Outro Visitante")
    )

    groups = models.ManyToManyField(
        AuthGroup,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set",
        related_query_name="customuser",
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="customuser_set",
        related_query_name="customuser",
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _("Usuário")
        verbose_name_plural = _("Usuários")

    def clean(self):
        """Garante que apenas UMA Entidade de Registro esteja vinculada."""
        super().clean()

        vinculos = [
            self.registro_aluno, self.registro_professor, self.registro_colaborador,
            self.registro_responsavel, self.registro_ure, self.registro_visitante
        ]

        vinculos_validos = [v for v in vinculos if v is not None]
        num_vinculos = len(vinculos_validos)

        if num_vinculos > 1:
            raise ValidationError(
                _('Um usuário pode estar vinculado a, no máximo, uma única Entidade de Registro.')
            )

        if self.pk and self.tipo_usuario != CustomUserTipo.ADMIN and num_vinculos == 0:
            raise ValidationError(
                _('Usuários não-Administradores devem estar vinculados a uma Entidade de Registro (Aluno, Professor, etc.).')
            )

    @property
    def registro(self):
        """Propriedade para acessar o registro vinculado de forma simplificada."""
        if self.registro_aluno:
            return self.registro_aluno
        elif self.registro_professor:
            return self.registro_professor
        elif self.registro_colaborador:
            return self.registro_colaborador
        elif self.registro_responsavel:
            return self.registro_responsavel
        elif self.registro_ure:
            return self.registro_ure
        elif self.registro_visitante:
            return self.registro_visitante
        return None

    def __str__(self):
        registro = self.registro
        if registro:
            nome = registro.nome_completo
        else:
            nome = f"{self.first_name} {self.last_name}".strip() if self.first_name or self.last_name else self.username

        return f"{nome} ({self.get_tipo_usuario_display()})"


# ==============================================================================
# 3. PROFILE (Dados Adicionais do Usuário)
# ==============================================================================

class Profile(models.Model):
    """Informações adicionais do usuário, fora do modelo base (CustomUser)."""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_("Usuário Associado")
    )

    data_nascimento = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Data de Nascimento")
    )

    # CORREÇÃO: Campo 'endereco' reinserido como bloco de texto (conforme solicitado).
    # Campos de endereço separados (cep, logradouro, etc.) foram removidos.
    endereco = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Endereço Completo")
    )

    whatsapp = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("Número WhatsApp")
    )

    outro_contato = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("Outro Contato (Ex: Telefone Fixo)")
    )

    foto_perfil = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True,
        verbose_name=_("Foto de Perfil")
    )
    cidade = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Cidade")
    )
    estado = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("Estado (UF)")
    )

    bio = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Mini-biografia ou Status")
    )

    class Meta:
        verbose_name = _("Perfil do Usuário")
        verbose_name_plural = _("Perfis dos Usuários")

    def __str__(self):
        return f"Perfil de {self.user.username}"


# ==============================================================================
# 4. GRUPOS DE AUDIÊNCIA (Motor de Segmentação e Permissões)
# ==============================================================================

class Grupo(models.Model):
    """Adiciona metadados ao modelo Group padrão do Django (AuthGroup)."""

    auth_group = models.OneToOneField(
        AuthGroup,
        on_delete=models.CASCADE,
        related_name='grupo_ranieri',
        verbose_name=_("Grupo de Autenticação Django")
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoGrupo.choices,
        default=TipoGrupo.TURMA,
        verbose_name=_("Tipo de Grupo")
    )

    descricao = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Descrição do Grupo")
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name=_("Grupo Ativo")
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Grupo de Audiência")
        verbose_name_plural = _("Grupos de Audiência")

    def __str__(self):
        return self.auth_group.name

    @property
    def membros(self):
        """Retorna os membros CustomUser que pertencem a este grupo."""
        return self.auth_group.customuser_set.all()


class MembroGrupo(models.Model):
    """Tabela de ligação que associa uma Entidade de Registro a um Grupo."""

    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.CASCADE,
        related_name='membros_registro',
        verbose_name=_("Grupo")
    )

    aluno = models.ForeignKey(
        RegistroAluno,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro Aluno")
    )
    professor = models.ForeignKey(
        RegistroProfessor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro Professor")
    )
    colaborador = models.ForeignKey(
        RegistroColaborador,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro Colaborador")
    )
    responsavel = models.ForeignKey(
        RegistroResponsavel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro Responsável")
    )
    ure = models.ForeignKey(
        RegistroURE,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro URE")
    )
    visitante = models.ForeignKey(
        RegistroOutrosVisitantes,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Registro Outro Visitante")
    )

    class Meta:
        verbose_name = _("Membro do Grupo de Audiência")
        verbose_name_plural = _("Membros do Grupo de Audiência")

    def clean(self):
        """Garante que apenas UMA das Entidades de Registro seja preenchida."""
        registros = [
            self.aluno, self.professor, self.colaborador,
            self.responsavel, self.ure, self.visitante
        ]

        registros_validos = [r for r in registros if r is not None]

        if len(registros_validos) != 1:
            raise ValidationError(
                _('Um Membro Grupo deve estar associado a exatamente uma Entidade de Registro.')
            )

    @property
    def registro(self):
        """Retorna a instância de registro vinculada."""
        if self.aluno:
            return self.aluno
        elif self.professor:
            return self.professor
        elif self.colaborador:
            return self.colaborador
        elif self.responsavel:
            return self.responsavel
        elif self.ure:
            return self.ure
        elif self.visitante:
            return self.visitante
        return None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        registro = self.registro
        registro_name = registro.nome_completo if registro else "Registro Desconhecido"
        return f"{registro_name} no grupo {self.grupo.auth_group.name}"

