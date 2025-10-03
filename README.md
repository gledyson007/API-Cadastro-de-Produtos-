# API de Busca Híbrida e Relevância de Produtos

## 📄 Resumo
Esta é uma API REST inteligente, construída com Django e Python, projetada para resolver o problema de busca e padronização de informações de produtos. A solução utiliza uma arquitetura híbrida "Firebase First" que combina uma busca em tempo real na web (via API da Serper) com um banco de dados NoSQL próprio (Firebase/Firestore) que atua como um "cache inteligente".

O sistema aprende com a interação do usuário através de um sistema de pontuação (score), ordenando os resultados das buscas por relevância e popularidade. A API é protegida por um sistema de autenticação moderno baseado em Tokens JWT, gerenciado pelo Firebase Authentication.

## ✨ Funcionalidades Principais
- **Busca Híbrida "Firebase First"**: A API prioriza a busca no banco de dados interno, garantindo respostas rápidas e baixo custo. A API externa só é consultada para descobrir produtos novos.
- **Sistema de Relevância por Votos**: Um endpoint de "votação" permite que aplicações clientes incrementem a pontuação de popularidade dos produtos. Os resultados da busca são sempre ordenados pela maior pontuação.
- **Processamento em Lote (Bulk)**: O endpoint de parse é capaz de receber uma lista de textos de produtos e retornar todos eles processados e enriquecidos em uma única chamada.
- **Parse e Enriquecimento de Dados**: A API utiliza Expressões Regulares (RegEx) para extrair dados estruturados (nome, preço, unidade) de um texto cru e enriquece o resultado com dados adicionais (imagem, descrição) buscados na web ou no banco de dados.
- **Autenticação Segura via Firebase JWT**: Todos os endpoints são protegidos, exigindo um Bearer Token válido gerado pelo Firebase Authentication.

## 🏗️ Arquitetura
O fluxo de dados prioriza o cache interno (Firebase/Firestore) para máxima performance e economia, recorrendo à busca externa apenas quando necessário:

```
┌──────────────┐        Requisição         ┌──────────────┐
│   Cliente    │ ───────────────────────▶ │    API DRF   │
│ (Frontend/   │                         │   (Django)   │
│   Postman)   │ ◀─────────────────────── │              │
└──────────────┘        Resposta          └──────────────┘
                                         │
                                         │
                                         ▼
                              ┌────────────────────┐
                              │   Firebase/        │
                              │   Firestore (DB)   │
                              └────────────────────┘
                                         │
                                         │ (Fallback: só consulta se não encontrar no DB)
                                         ▼
                              ┌────────────────────┐
                              │    Serper API      │
                              └────────────────────┘
```

- O cliente faz a requisição para a API.
- A API busca primeiro no Firestore (cache local).
- Se não encontrar, consulta a Serper API para dados externos.
- O resultado pode ser salvo no Firestore para futuras buscas rápidas.

## 🛠️ Tecnologias Utilizadas
- **Backend**: Python, Django, Django REST Framework (DRF)
- **Banco de Dados**: Google Firebase (Cloud Firestore)
- **Autenticação**: Firebase Authentication
- **Fonte de Dados Externa**: Serper API
- **Principais Bibliotecas**: firebase-admin, requests, drf-firebase-auth, django-cors-headers, python-dotenv.

## 🚀 Guia de Instalação e Uso
### Pré-requisitos
- Python 3.8+
- pip e venv

### Instalação Local
Clone o repositório:

```bash
git clone [URL_DO_SEU_REPOSITORIO_NO_GITHUB]
cd [NOME_DA_PASTA_DO_PROJETO]
```

Crie e ative o ambiente virtual:

```bash
# No Windows
python -m venv venv
.\venv\Scripts\activate

# No macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Configure as Variáveis de Ambiente
Crie um arquivo chamado `.env` na raiz do projeto.

Adicione sua chave da API da Serper:

```
SERPER_API_KEY="sua_chave_secreta_aqui"
```

### Configure as Credenciais do Firebase
- Baixe o seu arquivo de credenciais de Conta de Serviço do Firebase Console.
- Salve-o na raiz do projeto com o nome `firebase-credentials.json`.
- **Importante:** Adicione `firebase-credentials.json` e `.env` ao seu arquivo `.gitignore` para não enviar segredos para o GitHub!

### Executando o Servidor
Com o ambiente virtual ativado, rode o comando:

```bash
python manage.py runserver
```

A API estará disponível em http://127.0.0.1:8000/.

## 📖 Documentação da API
> Todos os endpoints exigem um cabeçalho de autenticação: `Authorization: Bearer <ID_TOKEN_FIREBASE>`

### 1. Processar Produtos em Lote
Processa uma lista de textos de produtos.

- **Endpoint:** `POST /v1/products/parse/`
- **Body (JSON):**

```json
{
    "terms": [
        "Leite Ninho lata 380g R$ 23,90",
        "Coca Cola 2L R$ 12,90"
    ]
}
```
- **Resposta (200 OK):** Um array `[]` de objetos de produtos processados.

### 2. Buscar ou Listar Produtos
Endpoint multifuncional para busca ou listagem.

- **Endpoint:** `GET /v1/products/standardize/`
- **Funcionalidade:**
    - Para buscar: Adicione um parâmetro `q`. Ex: `/?q=leite`
    - Para listar tudo: Chame o endpoint sem o parâmetro `q`.
- **Resposta (200 OK):** Um array `[]` de objetos de produtos, ordenado por score.

### 3. Incrementar Pontuação (Votar)
Registra um "voto" para um produto, incrementando seu score.

- **Endpoint:** `POST /v1/products/<product_id>/increment_score/`
- **Parâmetro de URL:** `product_id` (o slug do produto, ex: leite-ninho-lata-380g).
- **Body (JSON):** Deve conter o objeto completo do produto, para que ele possa ser criado caso não exista no banco.
- **Resposta (200 OK):** `{ "success": "Pontuação processada." }`

---

## 📊 Badges
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Django](https://img.shields.io/badge/django-4.x-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 💡 Exemplos de Uso (curl)
### Buscar produto
```bash
curl -H "Authorization: Bearer <TOKEN>" "http://127.0.0.1:8000/v1/products/standardize/?q=leite"
```

### Processar produtos em lote
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
    -d '{"terms": ["Leite Ninho lata 380g R$ 23,90", "Coca Cola 2L R$ 12,90"]}' \
    http://127.0.0.1:8000/v1/products/parse/
```

## ❓ FAQ
- **Preciso de uma conta no Firebase?**
  Sim, para autenticação e uso do Firestore.
- **Posso rodar sem a Serper API?**
  Não, ela é necessária para buscas externas.
- **Como obtenho o token JWT?**
  Pelo Firebase Authentication, via frontend ou SDK.

## 🧪 Testes Automatizados
Se houver testes, rode:
```bash
python manage.py test
```

## 📄 Licença
Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 👥 Créditos e Contato
Desenvolvido por Gledyson Cruz — fgledyson5@gmail.com


## 🔗 Links Úteis
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Serper API](https://serper.dev/)
