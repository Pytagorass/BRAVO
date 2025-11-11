from django.urls import path
from . import views

urlpatterns = [
    
    # --- Rotas de Autenticação e Gestão ---
    path('login/', views.login_view, name='login_view'),
    path('perfil/', views.usuario_perfil_view, name='usuario_perfil_view'),
    path('gestao/indicadores/', views.get_indicadores_gestao, name='get_indicadores_gestao'),

    # --- Rotas de CRUD (Quartos, Hóspedes) ---
    path('quartos/', views.quartos_view, name='quartos_view'),
    path('quartos/<int:quarto_id>/', views.quarto_detail_view, name='quarto_detail_view'),
    path('hospedes/', views.hospedes_view, name='hospedes_view'),
    path('hospedes/<int:hospede_id>/', views.hospede_detail_view, name='hospede_detail_view'),
    
    # --- Rotas de Reservas (Gantt) ---
    
    # POST: /api/reservas/ (Usado pelo NovaReservaModal para criar)
    path('reservas/', views.reservas_view, name='reservas_view'),
    
    # GET: /api/agenda/ (Usado pelo Gantt para carregar)
    path('agenda/', views.get_agenda_reservas, name='get_agenda_reservas'),
    
    # GET: /api/agenda/detalhes/<id>/ (Usado pelo ReservaDetalhesModal)
    path('agenda/detalhes/<int:reserva_quarto_id>/', views.get_reserva_detalhes, name='get_reserva_detalhes'),
    
    # PATCH: /api/agenda/update-status/<id>/ (Usado para Ações Rápidas - Pagar/Cancelar)
    path('agenda/update-status/<int:reserva_quarto_id>/', views.update_reserva_status_view, name='update_reserva_status'),
    
    # ROTA DE EDIÇÃO
    # PUT: /api/agenda/editar/<id>/ (Usado pelo formulário de Edição)
    path('agenda/editar/<int:reserva_quarto_id>/', views.edit_reserva_view, name='edit_reserva_view'),
]