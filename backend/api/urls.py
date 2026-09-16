from django.urls import path
from . import views

urlpatterns = [
    
    # --- Rotas de Autenticação e Gestão ---
    path('login/', views.login_view, name='login_view'),
    path('perfil/', views.usuario_perfil_view, name='usuario_perfil_view'),
    path('gestao/indicadores/', views.get_indicadores_gestao, name='get_indicadores_gestao'),
    path('gestao/reservas-pendentes/', views.get_reservas_pendentes, name='get_reservas_pendentes'),

    # --- Rotas de CRUD (Quartos, Hóspedes) ---
    # (GET, POST)
    path('quartos/', views.quartos_view, name='quartos_view'),
    # (GET, PUT, DELETE)
    path('quartos/<int:quarto_id>/', views.quarto_detail_view, name='quarto_detail_view'),
    
    # (GET, POST)
    path('hospedes/', views.hospedes_view, name='hospedes_view'),
    # (GET, PUT, DELETE)
    path('hospedes/<int:hospede_id>/', views.hospede_detail_view, name='hospede_detail_view'),

    # --- Rotas Operacionais (Barcos e Passeios) ---
    path('barcos/', views.barcos_view, name='barcos_view'),
    path('barcos/<int:barco_id>/', views.barco_detail_view, name='barco_detail_view'),
    path('tipos-passeio/', views.tipos_passeio_view, name='tipos_passeio_view'),
    
    # --- Rotas de Reservas (Gantt) ---
    
    # POST: /api/reservas/ (Usado pelo NovaReservaModal para criar)
    #    (Altere 'reservas_view' em views.py para 'create_reserva_view' se preferir)
    path('reservas/create/', views.reservas_view, name='reservas_view'),
    
    # GET: /api/agenda/ (Usado pelo Gantt para carregar)
    path('agenda/', views.get_agenda_reservas, name='get_agenda_reservas'),
    
    # GET: /api/agenda/detalhes/<id>/ (Usado pelo ReservaDetalhesModal)
    path('agenda/detalhes/<int:reserva_quarto_id>/', views.get_reserva_detalhes, name='get_reserva_detalhes'),
    
    # PATCH: /api/agenda/update-status/<id>/ (Usado para Ações Rápidas - Pagar/Cancelar)
    path('agenda/update-status/<int:reserva_quarto_id>/', views.update_reserva_status_view, name='update_reserva_status'),
    
    # PUT: /api/agenda/editar/<id>/ (Usado pelo formulário de Edição)
    path('agenda/editar/<int:reserva_quarto_id>/', views.edit_reserva_view, name='edit_reserva_view'),
    # --- Rotas de Consumo (Restaurante, Bar e Lojinha) ---
    path('consumo/categorias/', views.consumo_categorias_view, name='consumo_categorias'),
    path('consumo/produtos/', views.consumo_produtos_view, name='consumo_produtos'),
    path('consumo/produtos/<int:produto_id>/', views.consumo_produto_detail_view, name='consumo_produto_detail'),
    path('consumo/reservas-abertas/', views.consumo_reservas_abertas_view, name='consumo_reservas_abertas'),
    path('consumo/vendas/', views.consumo_vendas_view, name='consumo_vendas'),
    path('consumo/contas/<int:conta_id>/', views.consumo_conta_detail_view, name='consumo_conta_detail'),
    path('consumo/contas/<int:conta_id>/fechar/', views.consumo_fechar_conta_view, name='consumo_fechar_conta'),
]
