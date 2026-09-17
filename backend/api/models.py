from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, Permission, PermissionsMixin
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(email_usuario__iexact=username)

    def create_user(self, email_usuario, password=None, **extra_fields):
        if not email_usuario:
            raise ValueError('O email do usuario e obrigatorio.')

        email_usuario = self.normalize_email(email_usuario)
        extra_fields.setdefault('nome_usuario', email_usuario)
        extra_fields.setdefault('tipo_usuario', 'Recepcao')
        extra_fields.setdefault('ativo', 'Ativo')

        usuario = self.model(email_usuario=email_usuario, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email_usuario, password=None, **extra_fields):
        extra_fields.setdefault('nome_usuario', email_usuario)
        extra_fields.setdefault('tipo_usuario', 'Gerente')
        extra_fields.setdefault('ativo', 'Ativo')
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser precisa ter is_superuser=True.')

        return self.create_user(email_usuario, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True)
    nome_usuario = models.CharField(max_length=100)
    email_usuario = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255, db_column='senha')
    tipo_usuario = models.CharField(max_length=30)
    ativo = models.CharField(max_length=20, default='Ativo')
    groups = models.ManyToManyField(
        Group,
        blank=True,
        db_table='usuario_groups',
        related_name='usuarios_custom',
        related_query_name='usuario_custom',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        db_table='usuario_user_permissions',
        related_name='usuarios_custom',
        related_query_name='usuario_custom',
    )

    USERNAME_FIELD = 'email_usuario'
    REQUIRED_FIELDS = ['nome_usuario']

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.nome_usuario

    @property
    def senha(self):
        return self.password

    @senha.setter
    def senha(self, value):
        self.password = value

    @property
    def is_active(self):
        return self.ativo == 'Ativo'

    @is_active.setter
    def is_active(self, value):
        self.ativo = 'Ativo' if value else 'Inativo'

    @property
    def is_staff(self):
        return self.tipo_usuario in ('Gerente', 'Administrador')


class Hospede(models.Model):
    id_hospede = models.AutoField(primary_key=True)
    nome_hospede = models.CharField(max_length=100)
    email_hospede = models.CharField(max_length=100)
    telefone = models.CharField(max_length=30, null=True, blank=True)
    pais_origem = models.CharField(max_length=50)
    passaporte = models.CharField(max_length=30, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    ativo = models.CharField(max_length=20, default='Ativo')

    class Meta:
        db_table = 'hospede'

    def __str__(self):
        return self.nome_hospede


class Quarto(models.Model):
    id_quarto = models.AutoField(primary_key=True)
    numero = models.CharField(max_length=10)
    tipo_quarto = models.CharField(max_length=30)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    status_quarto = models.CharField(max_length=30, default='Dispon\u00edvel')

    class Meta:
        db_table = 'quarto'
        ordering = ['numero']

    def __str__(self):
        return self.numero


class Barco(models.Model):
    id_barco = models.AutoField(primary_key=True)
    nome_barco = models.CharField(max_length=100)
    capacidade_pessoas = models.IntegerField()
    status_barco = models.CharField(max_length=30, default='Dispon\u00edvel')
    observacao = models.TextField(null=True, blank=True)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'barco'
        ordering = ['nome_barco']

    def __str__(self):
        return self.nome_barco


class TipoPasseio(models.Model):
    id_tipo_passeio = models.AutoField(primary_key=True)
    nome_tipo = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    ativo = models.CharField(max_length=20, default='Ativo')
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tipo_passeio'
        ordering = ['nome_tipo']

    def __str__(self):
        return self.nome_tipo


class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    dt_criacao = models.DateTimeField(default=timezone.now)
    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    observacao_reserva = models.TextField(null=True, blank=True)
    hospede_titular = models.ForeignKey(
        Hospede,
        models.DO_NOTHING,
        db_column='fk_hospede_titular',
        null=True,
        blank=True,
        related_name='reservas_titular',
    )
    status_reserva = models.CharField(max_length=30, default='Agendada')
    status_pagamento = models.CharField(max_length=30, default='Pendente')
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='fk_usuario',
        related_name='reservas_criadas',
    )
    barco = models.ForeignKey(
        Barco,
        models.DO_NOTHING,
        db_column='fk_barco',
        null=True,
        blank=True,
        related_name='reservas',
    )
    tipo_passeio = models.ForeignKey(
        TipoPasseio,
        models.DO_NOTHING,
        db_column='fk_tipo_passeio',
        null=True,
        blank=True,
        related_name='reservas',
    )
    data_embarque = models.DateField(null=True, blank=True)
    data_desembarque = models.DateField(null=True, blank=True)
    local_embarque = models.CharField(max_length=120, null=True, blank=True)
    local_desembarque = models.CharField(max_length=120, null=True, blank=True)
    status_operacional = models.CharField(max_length=30, default='A Preparar')
    observacao_operacional = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reserva'

    def __str__(self):
        return f'Reserva #{self.id_reserva}'


class ReservaQuarto(models.Model):
    id_reserva_quarto = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='quartos_reservados',
    )
    quarto = models.ForeignKey(
        Quarto,
        models.DO_NOTHING,
        db_column='fk_quarto',
        related_name='reservas_quarto',
    )
    checkin = models.DateField()
    checkout = models.DateField()
    valor_diaria_cobrado = models.DecimalField(max_digits=10, decimal_places=2)
    desconto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )

    class Meta:
        db_table = 'reserva_quarto'

    def __str__(self):
        return f'{self.quarto} - {self.checkin}'


class ReservaHospede(models.Model):
    id_reserva_hospede = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='hospedes_adicionais',
    )
    hospede = models.ForeignKey(
        Hospede,
        models.DO_NOTHING,
        db_column='fk_hospede',
        related_name='reservas_acompanhante',
    )

    class Meta:
        db_table = 'reserva_hospede'


class ReservaPasseioDia(models.Model):
    id_reserva_passeio_dia = models.AutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='passeios_dia',
    )
    tipo_passeio = models.ForeignKey(
        TipoPasseio,
        models.DO_NOTHING,
        db_column='fk_tipo_passeio',
        null=True,
        blank=True,
        related_name='reservas_passeio_dia',
    )
    dia_viagem = models.IntegerField()
    data_passeio = models.DateField(null=True, blank=True)
    titulo = models.CharField(max_length=120, null=True, blank=True)
    local_previsto = models.CharField(max_length=120, null=True, blank=True)
    observacao = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reserva_passeio_dia'


class CategoriaProduto(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nome_categoria = models.CharField(max_length=100)
    tipo_categoria = models.CharField(max_length=30)
    ativo = models.CharField(max_length=20, default='Ativo')
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'categoria_produto'
        ordering = ['tipo_categoria', 'nome_categoria']

    def __str__(self):
        return self.nome_categoria


class Produto(models.Model):
    id_produto = models.AutoField(primary_key=True)
    categoria = models.ForeignKey(
        CategoriaProduto,
        models.DO_NOTHING,
        db_column='fk_categoria',
        related_name='produtos',
    )
    nome_produto = models.CharField(max_length=120)
    descricao = models.TextField(null=True, blank=True)
    preco_atual = models.DecimalField(max_digits=10, decimal_places=2)
    controla_estoque = models.BooleanField(default=False)
    estoque_atual = models.IntegerField(default=0)
    estoque_minimo = models.IntegerField(default=0)
    ativo = models.CharField(max_length=20, default='Ativo')
    dt_criacao = models.DateTimeField(default=timezone.now)
    dt_atualizacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'produto'
        ordering = ['nome_produto']

    def __str__(self):
        return self.nome_produto


class ContaConsumo(models.Model):
    id_conta = models.AutoField(primary_key=True)
    reserva = models.OneToOneField(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='conta_consumo',
    )
    total_acumulado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    status_conta = models.CharField(max_length=30, default='Aberta')
    dt_abertura = models.DateTimeField(default=timezone.now)
    dt_fechamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conta_consumo'

    def __str__(self):
        return f'Conta #{self.id_conta}'


class VendaConsumo(models.Model):
    id_venda = models.AutoField(primary_key=True)
    conta = models.ForeignKey(
        ContaConsumo,
        models.DO_NOTHING,
        db_column='fk_conta',
        related_name='vendas',
    )
    reserva = models.ForeignKey(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='vendas_consumo',
    )
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='fk_usuario',
        related_name='vendas_consumo',
    )
    origem = models.CharField(max_length=30)
    status_venda = models.CharField(max_length=30, default='Confirmada')
    observacao = models.TextField(null=True, blank=True)
    total_venda = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    dt_criacao = models.DateTimeField(default=timezone.now)
    dt_cancelamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'venda_consumo'


class ItemVendaConsumo(models.Model):
    id_item = models.AutoField(primary_key=True)
    venda = models.ForeignKey(
        VendaConsumo,
        models.DO_NOTHING,
        db_column='fk_venda',
        related_name='itens',
    )
    produto = models.ForeignKey(
        Produto,
        models.DO_NOTHING,
        db_column='fk_produto',
        related_name='itens_vendidos',
    )
    quantidade = models.IntegerField()
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(null=True, blank=True)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'item_venda_consumo'


class MovimentoEstoque(models.Model):
    id_movimento = models.AutoField(primary_key=True)
    produto = models.ForeignKey(
        Produto,
        models.DO_NOTHING,
        db_column='fk_produto',
        related_name='movimentos_estoque',
    )
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='fk_usuario',
        related_name='movimentos_estoque',
    )
    item_venda = models.ForeignKey(
        ItemVendaConsumo,
        models.DO_NOTHING,
        db_column='fk_item_venda',
        null=True,
        blank=True,
        related_name='movimentos_estoque',
    )
    tipo_movimento = models.CharField(max_length=30)
    quantidade = models.IntegerField()
    estoque_anterior = models.IntegerField()
    estoque_posterior = models.IntegerField()
    observacao = models.TextField(null=True, blank=True)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'movimento_estoque'


class CategoriaLavanderia(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nome_categoria = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    ativo = models.CharField(max_length=20, default='Ativo')
    ordem_exibicao = models.IntegerField(default=0)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'categoria_lavanderia'
        ordering = ['ordem_exibicao', 'nome_categoria']

    def __str__(self):
        return self.nome_categoria


class ServicoLavanderia(models.Model):
    id_servico = models.AutoField(primary_key=True)
    categoria = models.ForeignKey(
        CategoriaLavanderia,
        models.DO_NOTHING,
        db_column='fk_categoria',
        related_name='servicos',
    )
    nome_servico = models.CharField(max_length=120)
    descricao = models.TextField(null=True, blank=True)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    prazo_horas = models.IntegerField(default=24)
    ativo = models.CharField(max_length=20, default='Ativo')
    dt_criacao = models.DateTimeField(default=timezone.now)
    dt_atualizacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'servico_lavanderia'
        ordering = ['nome_servico']

    def __str__(self):
        return self.nome_servico


class OrdemLavanderia(models.Model):
    id_ordem = models.AutoField(primary_key=True)
    conta = models.ForeignKey(
        ContaConsumo,
        models.DO_NOTHING,
        db_column='fk_conta',
        related_name='ordens_lavanderia',
    )
    reserva = models.ForeignKey(
        Reserva,
        models.DO_NOTHING,
        db_column='fk_reserva',
        related_name='ordens_lavanderia',
    )
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='fk_usuario',
        related_name='ordens_lavanderia',
    )
    status_ordem = models.CharField(max_length=30, default='Recebido')
    observacao = models.TextField(null=True, blank=True)
    total_ordem = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    dt_recebimento = models.DateTimeField(default=timezone.now)
    dt_previsao_entrega = models.DateTimeField(null=True, blank=True)
    dt_entrega = models.DateTimeField(null=True, blank=True)
    dt_cancelamento = models.DateTimeField(null=True, blank=True)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ordem_lavanderia'


class ItemOrdemLavanderia(models.Model):
    id_item = models.AutoField(primary_key=True)
    ordem = models.ForeignKey(
        OrdemLavanderia,
        models.DO_NOTHING,
        db_column='fk_ordem',
        related_name='itens',
    )
    servico = models.ForeignKey(
        ServicoLavanderia,
        models.DO_NOTHING,
        db_column='fk_servico',
        related_name='itens_ordem',
    )
    quantidade = models.IntegerField()
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    observacao = models.TextField(null=True, blank=True)
    dt_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'item_ordem_lavanderia'


class HistoricoLavanderiaStatus(models.Model):
    id_historico = models.AutoField(primary_key=True)
    ordem = models.ForeignKey(
        OrdemLavanderia,
        models.DO_NOTHING,
        db_column='fk_ordem',
        related_name='historico_status',
    )
    status_anterior = models.CharField(max_length=30, null=True, blank=True)
    status_novo = models.CharField(max_length=30)
    usuario = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='fk_usuario',
        related_name='historicos_lavanderia',
    )
    observacao = models.TextField(null=True, blank=True)
    dt_alteracao = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'historico_lavanderia_status'
