import datetime

from ..repositories import gestao_repository


def buscar_indicadores(request):
    try:
        ano_filtrar = int(request.GET.get('ano', datetime.datetime.now().year))
    except ValueError:
        ano_filtrar = datetime.datetime.now().year

    return gestao_repository.buscar_indicadores(ano_filtrar)


def buscar_reservas_pendentes():
    return {'reservas': gestao_repository.buscar_reservas_pendentes()}
