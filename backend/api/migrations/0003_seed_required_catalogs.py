from decimal import Decimal

from django.db import migrations
from django.utils import timezone


def seed_required_catalogs(apps, schema_editor):
    TipoPasseio = apps.get_model('api', 'TipoPasseio')
    CategoriaProduto = apps.get_model('api', 'CategoriaProduto')
    CategoriaLavanderia = apps.get_model('api', 'CategoriaLavanderia')
    ServicoLavanderia = apps.get_model('api', 'ServicoLavanderia')

    tipos_passeio = [
        (
            'Pesca esportiva',
            'Roteiro focado em pesca esportiva com devolucao dos peixes, pontos combinados e suporte de guia.',
        ),
        (
            'Pesca tradicional',
            'Roteiro focado em pesca tradicional, conforme regras locais e combinados da operacao.',
        ),
        (
            'Contemplativo',
            'Passeio de descanso, navegacao, banho de rio e contemplacao da paisagem.',
        ),
        (
            'Observacao de aves',
            'Roteiro focado em observacao de aves, fauna, fotografia e paradas silenciosas.',
        ),
        (
            'Misto',
            'Roteiro personalizado combinando pesca, contemplacao, banho de rio e paradas especiais.',
        ),
        (
            'Corporativo',
            'Roteiro para grupos fechados, eventos, confraternizacoes e experiencias privativas.',
        ),
        (
            'Familia',
            'Roteiro leve para familias, com horarios flexiveis e atividades de baixa intensidade.',
        ),
    ]

    for nome_tipo, descricao in tipos_passeio:
        TipoPasseio.objects.update_or_create(
            nome_tipo=nome_tipo,
            defaults={
                'descricao': descricao,
                'ativo': 'Ativo',
            },
        )

    categorias_produto = [
        ('Bebidas', 'Restaurante', 'Ativo'),
        ('Lembrancas', 'Lojinha', 'Ativo'),
        ('Vestuarios', 'Lojinha', 'Ativo'),
        ('Utilidades', 'Lojinha', 'Ativo'),
        ('Pesca', 'Lojinha', 'Ativo'),
    ]

    for nome_categoria, tipo_categoria, ativo in categorias_produto:
        CategoriaProduto.objects.update_or_create(
            nome_categoria=nome_categoria,
            tipo_categoria=tipo_categoria,
            defaults={'ativo': ativo},
        )

    CategoriaProduto.objects.filter(
        tipo_categoria='Restaurante',
    ).exclude(
        nome_categoria='Bebidas',
    ).update(ativo='Inativo')

    categorias_lavanderia = [
        (
            'Roupas leves',
            'Pecas leves de uso diario dos turistas.',
            10,
        ),
        (
            'Roupas pesadas',
            'Pecas mais volumosas ou de tecido pesado.',
            20,
        ),
        (
            'Roupas especiais',
            'Pecas de pesca, praia ou acessorios pessoais.',
            30,
        ),
    ]

    for nome_categoria, descricao, ordem_exibicao in categorias_lavanderia:
        CategoriaLavanderia.objects.update_or_create(
            nome_categoria=nome_categoria,
            defaults={
                'descricao': descricao,
                'ordem_exibicao': ordem_exibicao,
                'ativo': 'Ativo',
            },
        )

    categorias_lavanderia_por_nome = {
        categoria.nome_categoria: categoria
        for categoria in CategoriaLavanderia.objects.filter(
            nome_categoria__in=[categoria[0] for categoria in categorias_lavanderia],
        )
    }

    servicos_lavanderia = [
        ('Roupas leves', 'Camiseta', 'Lavagem de camiseta por peca.', '8.00', 24),
        ('Roupas leves', 'Camisa', 'Lavagem de camisa por peca.', '10.00', 24),
        ('Roupas leves', 'Regata', 'Lavagem de regata por peca.', '7.00', 24),
        ('Roupas leves', 'Short / Bermuda', 'Lavagem de short ou bermuda por peca.', '10.00', 24),
        ('Roupas leves', 'Roupa intima', 'Lavagem de roupa intima por peca.', '5.00', 24),
        ('Roupas leves', 'Meia', 'Lavagem de par de meias.', '4.00', 24),
        ('Roupas pesadas', 'Calca jeans', 'Lavagem de calca jeans por peca.', '16.00', 36),
        ('Roupas pesadas', 'Calca moletom', 'Lavagem de calca moletom por peca.', '14.00', 36),
        ('Roupas pesadas', 'Blusa de frio', 'Lavagem de blusa de frio por peca.', '18.00', 36),
        ('Roupas pesadas', 'Jaqueta', 'Lavagem de jaqueta por peca.', '22.00', 48),
        ('Roupas especiais', 'Camisa UV', 'Lavagem de camisa UV por peca.', '12.00', 24),
        ('Roupas especiais', 'Roupa de pesca', 'Lavagem de roupa de pesca por peca.', '15.00', 36),
        ('Roupas especiais', 'Chapeu / Bone', 'Lavagem de chapeu ou bone por peca.', '8.00', 24),
        ('Roupas especiais', 'Maio / Biquini / Sunga', 'Lavagem de roupa de banho pessoal por peca.', '7.00', 24),
    ]

    for nome_categoria, nome_servico, descricao, preco_unitario, prazo_horas in servicos_lavanderia:
        categoria = categorias_lavanderia_por_nome[nome_categoria]
        ServicoLavanderia.objects.update_or_create(
            categoria=categoria,
            nome_servico=nome_servico,
            defaults={
                'descricao': descricao,
                'preco_unitario': Decimal(preco_unitario),
                'prazo_horas': prazo_horas,
                'ativo': 'Ativo',
                'dt_atualizacao': timezone.now(),
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0002_database_constraints'),
    ]

    operations = [
        migrations.RunPython(seed_required_catalogs, migrations.RunPython.noop),
    ]
