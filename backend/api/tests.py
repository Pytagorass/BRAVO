import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from api.access_control import ROLE_GERENTE, ROLE_RECEPCAO
from api.auth_decorator import token_required
from api.models import (
    CategoriaLavanderia,
    CategoriaProduto,
    ContaConsumo,
    Hospede,
    ItemOrdemLavanderia,
    ItemVendaConsumo,
    OrdemLavanderia,
    Produto,
    Quarto,
    Reserva,
    ReservaQuarto,
    ServicoLavanderia,
    Usuario,
    VendaConsumo,
)
from api.responses import success_response
from api.services.auth_service import _gerar_tokens


class LoginViewTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/login/'

    def post_login(self, payload, content_type='application/json'):
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return self.client.post(self.url, data=data, content_type=content_type)

    def test_login_sem_credenciais_retorna_400(self):
        response = self.post_login({})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error']['code'], 'VALIDATION_ERROR')

    def test_login_com_json_invalido_retorna_400(self):
        response = self.post_login('{email')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error']['code'], 'INVALID_JSON')

    @patch('api.services.auth_service.authenticate')
    def test_login_usuario_inexistente_retorna_401(self, authenticate):
        authenticate.return_value = None

        response = self.post_login({'email': 'teste@teste.com', 'senha': '123456'})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error']['code'], 'AUTH_FAILED')
        authenticate.assert_called_once()

    @patch('api.services.auth_service.authenticate')
    def test_login_senha_incorreta_retorna_401(self, authenticate):
        authenticate.return_value = None

        response = self.post_login({'email': 'teste@teste.com', 'senha': 'senha-errada'})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error']['code'], 'AUTH_FAILED')

    @patch('api.services.auth_service.authenticate')
    def test_login_valido_retorna_token_e_usuario(self, authenticate):
        authenticate.return_value = SimpleNamespace(
            id_usuario=3,
            nome_usuario='Administrador',
            email_usuario='teste@teste.com',
            tipo_usuario='Gerente',
        )

        response = self.post_login({'email': 'teste@teste.com', 'senha': '123456'})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertIn('token', body['data'])
        self.assertEqual(body['data']['access'], body['data']['token'])
        self.assertIn('refresh', body['data'])
        self.assertEqual(body['data']['usuario']['id'], 3)
        self.assertEqual(body['data']['usuario']['nome'], 'Administrador')
        self.assertEqual(body['data']['usuario']['email'], 'teste@teste.com')
        self.assertEqual(body['data']['usuario']['tipo'], 'Gerente')
        self.assertIn('gestao.read', body['data']['usuario']['permissoes'])

        payload = jwt.decode(body['data']['token'], settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['id_usuario'], 3)
        self.assertEqual(payload['email'], 'teste@teste.com')


class RefreshTokenTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/token/refresh/'

    def post_refresh(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

    def test_refresh_sem_token_retorna_400(self):
        response = self.post_refresh({})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error']['code'], 'VALIDATION_ERROR')

    @patch('api.services.auth_service.auth_repository.buscar_usuario_ativo_por_id')
    def test_refresh_valido_retorna_novo_access_token(self, buscar_usuario):
        usuario = SimpleNamespace(
            id_usuario=3,
            nome_usuario='Administrador',
            email_usuario='teste@teste.com',
            tipo_usuario='Gerente',
        )
        buscar_usuario.return_value = usuario
        refresh = _gerar_tokens(usuario)['refresh']

        response = self.post_refresh({'refresh': refresh})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertIn('token', body['data'])
        self.assertIn('access', body['data'])
        self.assertIn('refresh', body['data'])
        self.assertEqual(body['data']['usuario']['id'], 3)
        buscar_usuario.assert_called_once_with(3)


class TokenRequiredTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _token_for(self, tipo_usuario='Recepcao'):
        usuario = SimpleNamespace(
            id_usuario=7,
            nome_usuario='Operador',
            email_usuario='operador@teste.com',
            tipo_usuario=tipo_usuario,
        )
        return _gerar_tokens(usuario)['access']

    def _protected_view(self):
        @token_required(roles=(ROLE_RECEPCAO,))
        def view(request):
            return success_response({'id_usuario': request.user_token_payload['id_usuario']})

        return view

    @patch('api.auth_decorator._get_active_usuario')
    def test_token_required_permite_perfil_autorizado(self, buscar_usuario):
        buscar_usuario.return_value = SimpleNamespace(
            id_usuario=7,
            nome_usuario='Recepcao',
            email_usuario='recepcao@teste.com',
            tipo_usuario='Recepcao',
        )
        request = self.factory.get(
            '/protegido/',
            HTTP_AUTHORIZATION=f'Bearer {self._token_for()}',
        )

        response = self._protected_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['data']['id_usuario'], 7)

    @patch('api.auth_decorator._get_active_usuario')
    def test_token_required_bloqueia_perfil_sem_permissao(self, buscar_usuario):
        buscar_usuario.return_value = SimpleNamespace(
            id_usuario=7,
            nome_usuario='Comercial',
            email_usuario='comercial@teste.com',
            tipo_usuario='Comercial',
        )
        request = self.factory.get(
            '/protegido/',
            HTTP_AUTHORIZATION=f'Bearer {self._token_for("Comercial")}',
        )

        response = self._protected_view()(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content)['error']['code'], 'FORBIDDEN')

    @patch('api.auth_decorator._get_active_usuario')
    def test_token_required_bloqueia_usuario_inativo(self, buscar_usuario):
        buscar_usuario.return_value = None
        request = self.factory.get(
            '/protegido/',
            HTTP_AUTHORIZATION=f'Bearer {self._token_for()}',
        )

        response = self._protected_view()(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)['error']['code'], 'AUTH_USER_INACTIVE')


class ContasEmBordoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/gestao/contas-em-bordo/'

        self.gerente = Usuario.objects.create_user(
            email_usuario='gerente@teste.com',
            password='123456',
            nome_usuario='Gerente Teste',
            tipo_usuario=ROLE_GERENTE,
        )
        self.recepcao = Usuario.objects.create_user(
            email_usuario='recepcao@teste.com',
            password='123456',
            nome_usuario='Recepcao Teste',
            tipo_usuario=ROLE_RECEPCAO,
        )

    def _auth_headers(self, usuario):
        token = _gerar_tokens(usuario)['access']
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def _criar_conta_com_lancamentos(self):
        hospede = Hospede.objects.create(
            nome_hospede='Joao Silva',
            email_hospede='joao@teste.com',
            telefone='65999990000',
            pais_origem='Brasil',
            cpf='123.456.789-09',
        )
        quarto = Quarto.objects.create(
            numero='101',
            tipo_quarto='Suite',
            valor_diaria=Decimal('500.00'),
            status_quarto='Disponivel',
        )
        reserva = Reserva.objects.create(
            valor_total=Decimal('1500.00'),
            hospede_titular=hospede,
            status_reserva='Ativa',
            status_pagamento='Pago',
            usuario=self.gerente,
            data_embarque=timezone.localdate(),
            data_desembarque=timezone.localdate() + timedelta(days=2),
        )
        ReservaQuarto.objects.create(
            reserva=reserva,
            quarto=quarto,
            checkin=timezone.localdate(),
            checkout=timezone.localdate() + timedelta(days=2),
            valor_diaria_cobrado=Decimal('500.00'),
        )
        conta = ContaConsumo.objects.create(
            reserva=reserva,
            total_acumulado=Decimal('45.00'),
            status_conta='Aberta',
        )
        categoria_produto, _ = CategoriaProduto.objects.get_or_create(
            nome_categoria='Bebidas',
            tipo_categoria='Restaurante',
        )
        produto = Produto.objects.create(
            categoria=categoria_produto,
            nome_produto='Agua mineral',
            preco_atual=Decimal('10.00'),
            controla_estoque=False,
        )
        venda = VendaConsumo.objects.create(
            conta=conta,
            reserva=reserva,
            usuario=self.gerente,
            origem='Restaurante',
            total_venda=Decimal('20.00'),
        )
        ItemVendaConsumo.objects.create(
            venda=venda,
            produto=produto,
            quantidade=2,
            valor_unitario=Decimal('10.00'),
            subtotal=Decimal('20.00'),
        )
        categoria_lavanderia, _ = CategoriaLavanderia.objects.get_or_create(
            nome_categoria='Roupas Leves',
            defaults={'ordem_exibicao': 1},
        )
        servico = ServicoLavanderia.objects.create(
            categoria=categoria_lavanderia,
            nome_servico='Camiseta',
            preco_unitario=Decimal('25.00'),
        )
        ordem = OrdemLavanderia.objects.create(
            conta=conta,
            reserva=reserva,
            usuario=self.gerente,
            total_ordem=Decimal('25.00'),
        )
        ItemOrdemLavanderia.objects.create(
            ordem=ordem,
            servico=servico,
            quantidade=1,
            valor_unitario=Decimal('25.00'),
            subtotal=Decimal('25.00'),
        )

    def test_contas_em_bordo_retorna_resumo_e_lancamentos_para_gerente(self):
        self._criar_conta_com_lancamentos()

        response = self.client.get(self.url, **self._auth_headers(self.gerente))

        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(data['resumo']['clientes_em_bordo'], 1)
        self.assertEqual(data['resumo']['contas_abertas'], 1)
        self.assertEqual(len(data['contas']), 1)
        conta = data['contas'][0]
        self.assertEqual(conta['hospede'], 'Joao Silva')
        self.assertEqual(conta['status_conta'], 'Aberta')
        self.assertEqual(conta['total_acumulado'], 45.0)
        self.assertEqual(conta['totais']['bebidas'], 20.0)
        self.assertEqual(conta['totais']['lavanderia'], 25.0)
        self.assertEqual(conta['quantidade_lancamentos'], 2)

    def test_contas_em_bordo_bloqueia_perfil_sem_acesso_total(self):
        response = self.client.get(self.url, **self._auth_headers(self.recepcao))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'FORBIDDEN')
