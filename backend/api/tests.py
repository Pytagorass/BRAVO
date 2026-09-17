import json
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import Client, RequestFactory, SimpleTestCase

from api.access_control import ROLE_RECEPCAO
from api.auth_decorator import token_required
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
            nome_usuario='Gestao',
            email_usuario='gestao@teste.com',
            tipo_usuario='Gestao',
        )
        request = self.factory.get(
            '/protegido/',
            HTTP_AUTHORIZATION=f'Bearer {self._token_for("Gestao")}',
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
