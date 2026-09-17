from .auth import login_view, refresh_token_view
from .barcos import barco_detail_view, barcos_view, tipos_passeio_view
from .consumo import (
    consumo_categorias_view,
    consumo_produto_detail_view,
    consumo_produtos_view,
)
from .consumo_operacional import (
    consumo_conta_detail_view,
    consumo_fechar_conta_view,
    consumo_reservas_abertas_view,
    consumo_vendas_view,
)
from .gestao import get_indicadores_gestao, get_reservas_pendentes
from .hospedes import hospede_detail_view, hospedes_view
from .lavanderia import (
    consumo_lavanderia_categorias_view,
    consumo_lavanderia_ordem_status_view,
    consumo_lavanderia_ordens_view,
    consumo_lavanderia_servicos_view,
)
from .quartos import quarto_detail_view, quartos_view
from .reservas import (
    edit_reserva_view,
    get_agenda_reservas,
    get_reserva_detalhes,
    reservas_view,
    update_reserva_status_view,
)
from .usuarios import usuario_perfil_view

__all__ = [
    'login_view',
    'refresh_token_view',
    'usuario_perfil_view',
    'get_indicadores_gestao',
    'get_reservas_pendentes',
    'quartos_view',
    'quarto_detail_view',
    'hospedes_view',
    'hospede_detail_view',
    'barcos_view',
    'barco_detail_view',
    'tipos_passeio_view',
    'reservas_view',
    'get_agenda_reservas',
    'get_reserva_detalhes',
    'update_reserva_status_view',
    'edit_reserva_view',
    'consumo_categorias_view',
    'consumo_produtos_view',
    'consumo_produto_detail_view',
    'consumo_reservas_abertas_view',
    'consumo_vendas_view',
    'consumo_lavanderia_categorias_view',
    'consumo_lavanderia_servicos_view',
    'consumo_lavanderia_ordens_view',
    'consumo_lavanderia_ordem_status_view',
    'consumo_conta_detail_view',
    'consumo_fechar_conta_view',
]
