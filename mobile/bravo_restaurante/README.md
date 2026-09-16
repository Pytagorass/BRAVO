# BRAVO Consumo Mobile

Aplicativo Flutter do projeto BRAVO para dispositivos moveis. Ele usa a API Django do projeto principal para autenticar usuarios, consultar reservas abertas, registrar consumo do restaurante, bar e lojinha, acompanhar contas de hospedes e fechar contas de consumo.

## Tecnologias

- Flutter
- Dart
- Provider para estado
- HTTP para comunicacao com a API Django
- PDF e Printing para relatorios
- Material Design

## Funcionalidades

- Login via `/api/login/`
- Listagem de reservas abertas
- Registro de itens do restaurante
- Registro de bebidas do bar
- Registro de produtos da lojinha
- Consulta da conta do hospede
- Fechamento da conta de consumo
- Geracao de comprovante em PDF

## Estrutura

```text
lib/
  main.dart                 # App, tema e Providers
  models/                   # Modelos consumidos da API
  mvvm/                     # ViewModels das telas
  pages/                    # Telas principais
  services/                 # Cliente HTTP e servicos da API Django
  widgets/                  # Componentes reutilizaveis

assets/
  LogoBravo.png
```

## API Django

O cliente HTTP fica em `lib/services/django_api_client.dart`.

Por padrao, o app usa:

```text
http://127.0.0.1:8000/api
```

Para alterar a URL, use `--dart-define=BRAVO_API_URL=...` ao rodar o app.

Exemplo para Android Emulator:

```powershell
flutter run --dart-define=BRAVO_API_URL=http://10.0.2.2:8000/api
```

Exemplo para aparelho fisico na mesma rede:

```powershell
flutter run --dart-define=BRAVO_API_URL=http://SEU_IP_LOCAL:8000/api
```

Nesse caso, rode o Django aceitando conexoes da rede:

```powershell
python manage.py runserver 0.0.0.0:8000
```

## Como Executar

Na raiz do monorepo:

```powershell
cd mobile\bravo_restaurante
flutter pub get
flutter run
```

Para validar o projeto:

```powershell
dart analyze
flutter test --no-pub
```

## Endpoints Usados

- `POST /api/login/`
- `GET /api/consumo/reservas-abertas/`
- `GET /api/consumo/produtos/`
- `POST /api/consumo/vendas/`
- `GET /api/consumo/contas/<id>/`
- `POST /api/consumo/contas/<id>/fechar/`

## Observacoes

- Restaurante e Lojinha usam a mesma tela de registro, mudando apenas a origem enviada para a API.
- Bar usa a mesma API de vendas, filtrando produtos da categoria de bebidas.
- O token JWT fica em memoria durante a sessao do app. Ao sair, ele e limpo.
