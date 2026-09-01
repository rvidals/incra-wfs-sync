# 🌐 Atualizador WFS — INCRA Glebas Remanescentes

Automação em Python para **consulta, comparação e atualização de dados geoespaciais do INCRA**, obtidos por meio de um serviço **WFS (Web Feature Service)**, diretamente em um banco de dados **PostgreSQL/PostGIS**.

O projeto foi desenvolvido para manter uma tabela geoespacial atualizada de forma automática, evitando a necessidade de realizar manualmente a consulta ao WFS e a atualização dos registros no banco.

---

## 📋 Funcionalidades

* 🔎 **Consulta automática** ao serviço WFS do INCRA
* 🌎 **Processamento de geometrias** no formato WFS
* 🔄 **Conversão e adequação de coordenadas** para utilização no PostGIS
* 🗄️ **Inserção de novos registros** no PostgreSQL
* ♻️ **Atualização de registros existentes**
* 🧠 **Comparação inteligente**, atualizando somente registros que realmente sofreram alterações
* 🚫 **Tratamento de duplicidades**, mantendo apenas um registro por GID
* 📦 **Processamento em lotes (batch)** para melhorar o desempenho
* 📝 **Sistema de logs** com registro detalhado das operações
* 🔐 **Configuração externa**, separando parâmetros de conexão e execução do código
* ⏰ Possibilidade de **execução automatizada por agendamento**

---

## 🛠️ Tecnologias

| Tecnologia         | Utilização                                     |
| ------------------ | ---------------------------------------------- |
| **Python 3.11+**   | Linguagem principal                            |
| **PostgreSQL 16+** | Banco de dados                                 |
| **PostGIS**        | Armazenamento e processamento espacial         |
| **psycopg2**       | Conexão com PostgreSQL                         |
| **pandas**         | Manipulação dos dados                          |
| **requests**       | Requisições HTTP ao WFS                        |
| **SQLAlchemy**     | Integração com banco de dados e pandas         |
| **WFS / OGC**      | Serviço de distribuição dos dados geoespaciais |

---

## 📁 Estrutura do projeto

```text
AtualizadorWFS/
│
├── atualizador_wfs.py       # Script principal
├── config.json              # Configurações da aplicação
├── config.example.json      # Modelo de configuração
├── requirements.txt         # Dependências Python
├── README.md                # Documentação
├── LICENSE                  # Licença do projeto
├── .gitignore               # Arquivos ignorados pelo Git
│
└── logs/
    └── atualizacao.log      # Registro das execuções
```

---

# ⚙️ Configuração

## 1. Arquivo `config.json`

O comportamento do sistema é controlado pelo arquivo `config.json`.

Recomenda-se manter no repositório apenas um arquivo de exemplo:

```text
config.example.json
```

e criar localmente:

```text
config.json
```

### Exemplo

```json
{
  "database": {
    "host": "HOST_DO_BANCO",
    "port": "PORTA",
    "database": "NOME_DO_BANCO",
    "user": "USUARIO",
    "password": "SENHA"
  },

  "wfs": {
    "url": "URL_DO_WFS",
    "type_name": "NAMESPACE:TYPENAME",
    "srsname": "EPSG:4326",
    "max_features": 50000
  },

  "table": {
    "name": "NOME_DA_TABELA",
    "schema": "NOME_DO_SCHEMA",
    "primary_key": [
      "gid"
    ]
  },

  "update": {
    "delete_orphans": false,
    "batch_size": 1000
  },

  "logging": {
    "level": "INFO",
    "file": "logs/atualizacao.log"
  }
}
```

> ⚠️ **Importante:** nunca publique credenciais reais de banco de dados no GitHub.

Adicione o arquivo `config.json` ao `.gitignore`:

```gitignore
config.json
logs/
*.log
```

---

# 🗄️ Estrutura da tabela

O script foi desenvolvido para trabalhar com uma tabela espacial contendo, entre outros campos, a geometria e o identificador `gid`.

Exemplo da estrutura utilizada:

```sql
CREATE TABLE IF NOT EXISTS bases_gerais.incra_remanescentes_de_glebas_ago_26
(
    fid bigint NOT NULL,
    geom geometry(MultiPolygon, 4326),
    gid character varying,
    cod_imovel character varying,
    matricula character varying,
    mat_recons character varying,
    nome_gleba character varying,
    sr character varying,
    uf character varying,
    situacao character varying,
    area_ha character varying,
    data_certi timestamp without time zone,
    num_certif character varying,
    assent_pre character varying,
    ano_assent character varying,
    id_gid character varying,
    gl_fora_am character varying,
    codigo_gle character varying,
    "Destinada" character varying,
    "OBS_1" character varying,
    area_re_ha character varying,

    CONSTRAINT incra_remanescentes_de_glebas_ago_26_pkey
        PRIMARY KEY (fid)
);
```

> A estrutura acima representa a tabela utilizada no projeto. Caso o destino seja outra tabela, os nomes do schema, tabela e campos devem ser ajustados de acordo com a estrutura do banco.

---

# 📦 Instalação

## 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/AtualizadorWFS.git
cd AtualizadorWFS
```

## 2. Criar um ambiente virtual

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

### Conda

```bash
conda create -n geopy_311 python=3.11
conda activate geopy_311
```

---

## 3. Instalar as dependências

Com `pip`:

```bash
pip install -r requirements.txt
```

---

# 🚀 Execução

Depois de configurar o `config.json`, execute:

```bash
python atualizador_wfs.py
```

O programa irá:

1. Carregar as configurações;
2. Consultar o serviço WFS do INCRA;
3. Processar o XML retornado;
4. Criar o DataFrame com os dados;
5. Processar as geometrias;
6. Conectar ao PostgreSQL/PostGIS;
7. Comparar os dados recebidos com os dados existentes;
8. Identificar registros novos;
9. Identificar registros alterados;
10. Atualizar somente os registros necessários;
11. Inserir novos registros;
12. Registrar todo o processo no log.

---

# 🔄 Fluxo de atualização

```text
              ┌──────────────────────┐
              │   config.json        │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Consulta ao WFS      │
              │       INCRA          │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Processamento XML    │
              │      → pandas        │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Processamento das    │
              │     geometrias       │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ PostgreSQL / PostGIS │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Comparação por GID   │
              └──────────┬───────────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
          Registro novo      Registro existente
                │                 │
                ▼                 ▼
             INSERT          Verificar alterações
                                  │
                                  ▼
                              UPDATE
                                  │
                                  ▼
                           Registrar no log
```

---

# 🧠 Estratégia de atualização

A atualização não consiste simplesmente em substituir toda a tabela.

O script utiliza o **GID como identificador do registro** e compara os dados provenientes do WFS com os registros existentes no banco.

### Registros novos

Quando um `gid` está presente no WFS, mas não existe na tabela:

```text
WFS        → GID 1234
Banco      → não existe

Resultado  → INSERT
```

### Registros existentes sem alteração

```text
WFS        → GID 5678
Banco      → GID 5678
Dados      → iguais

Resultado  → nenhuma alteração
```

### Registros existentes com alteração

```text
WFS        → GID 9012
Banco      → GID 9012
Dados      → diferentes

Resultado  → UPDATE
```

Essa estratégia reduz operações desnecessárias no banco e permite identificar exatamente quais registros foram modificados.

---

# 🚫 Tratamento de duplicidades

O serviço WFS pode retornar mais de uma ocorrência para o mesmo `gid`.

Nesses casos, o script considera apenas um registro por GID, evitando duplicidades na atualização da tabela.

---

# 🌎 Geometrias e coordenadas

O WFS utilizado pelo projeto disponibiliza as geometrias no sistema de referência configurado.

Por padrão, o projeto utiliza:

```text
EPSG:4326
```

As coordenadas são processadas para garantir a compatibilidade com a estrutura espacial do PostGIS.

A coluna de geometria da tabela de destino utiliza:

```sql
geometry(MultiPolygon, 4326)
```

---

# 📝 Logs

As execuções são registradas em:

```text
logs/atualizacao.log
```

As mensagens também são exibidas no console.

Exemplo:

```text
2026-08-31 14:15:39 - INFO - ============================================================
2026-08-31 14:15:39 - INFO - INICIANDO ATUALIZAÇÃO AUTOMÁTICA
2026-08-31 14:15:39 - INFO - Data/Hora: 2026-08-31 14:15:39
2026-08-31 14:15:39 - INFO - Configuração carregada com sucesso
2026-08-31 14:15:39 - INFO - Buscando dados do WFS
2026-08-31 14:15:50 - INFO - Requisição concluída
2026-08-31 14:15:51 - INFO - Encontradas 1186 features no XML
2026-08-31 14:15:51 - INFO - DataFrame criado
2026-08-31 14:15:52 - INFO - Conectando ao PostgreSQL
2026-08-31 14:15:52 - INFO - GIDs únicos no WFS: 1099
2026-08-31 14:15:52 - INFO - GIDs únicos na tabela: 1099
2026-08-31 14:15:52 - INFO - GIDs NOVOS (INSERT): 0
2026-08-31 14:15:52 - INFO - GIDs EXISTENTES: 1099
2026-08-31 14:15:52 - INFO - REGISTROS PARA UPDATE: 16
2026-08-31 14:15:53 - INFO - Transação commitada com sucesso!
2026-08-31 14:15:53 - INFO - Inseridos: 0
2026-08-31 14:15:53 - INFO - Atualizados: 16
2026-08-31 14:15:53 - INFO - Status: SUCESSO
```

---

# ⏰ Automação

O script pode ser executado automaticamente em intervalos definidos.

## Linux — Cron

Exemplo para execução diária às 06:00:

```bash
0 6 * * * /usr/bin/python3 /caminho/para/atualizador_wfs.py
```

Com Conda:

```bash
0 6 * * * /caminho/para/conda/envs/geopy_311/bin/python /caminho/para/atualizador_wfs.py
```

## Windows — Agendador de Tarefas

No Windows, configure uma tarefa com:

**Ação:** iniciar um programa

**Programa/script:**

```text
python.exe
```

**Argumentos:**

```text
C:\Scripts\AtualizadorWFS\atualizador_wfs.py
```

**Iniciar em:**

```text
C:\Scripts\AtualizadorWFS\
```

> Os caminhos devem ser ajustados de acordo com a instalação do Python/Conda e a localização do projeto.

---

# ⚠️ Considerações importantes

### 🔐 Segurança

Nunca versione:

* senhas;
* credenciais de banco;
* arquivos `config.json` com informações reais;
* logs contendo informações sensíveis.

Utilize `config.example.json` como modelo.

---

### 🗑️ Registros órfãos

Por padrão:

```json
"delete_orphans": false
```

Isso significa que registros existentes no banco **não são excluídos automaticamente** caso deixem de aparecer no WFS.

Essa configuração reduz o risco de remoções indevidas.

---

### 📦 Processamento em lote

As operações de banco são realizadas utilizando processamento em lotes.

O tamanho pode ser configurado através de:

```json
"batch_size": 1000
```

---

### 🔁 Idempotência

Uma das características importantes do processo é que executar o script repetidamente com os mesmos dados do WFS não deve gerar atualizações desnecessárias.

Se os registros não tiverem sofrido alterações:

```text
INSERT → 0
UPDATE → 0
```

---

# 🤝 Contribuição

Contribuições são bem-vindas.

Para contribuir:

```bash
# 1. Faça um fork do projeto

# 2. Crie uma branch
git checkout -b feature/nova-feature

# 3. Faça suas alterações

# 4. Commit
git commit -m "Adicionar nova feature"

# 5. Envie para o GitHub
git push origin feature/nova-feature
```

Depois, abra um **Pull Request**.

---

# 📄 Licença

Este projeto está disponível sob a licença **MIT**.

Consulte o arquivo [`LICENSE`](LICENSE) para mais informações.

---

# 👤 Autor

**Rogerio Siqueira**

Desenvolvedor de soluções geoespaciais.

---

# 📊 Status

🟢 **Em produção**

O script é utilizado para realizar a atualização automatizada de dados geoespaciais provenientes do WFS do INCRA.

---

## 📌 Roadmap

Possíveis melhorias futuras:

* [ ] Migrar credenciais do `config.json` para variáveis de ambiente
* [ ] Criar interface para acompanhamento das atualizações
* [ ] Implementar notificações após a execução
* [ ] Disponibilizar relatório resumido de cada atualização
* [ ] Adicionar testes automatizados
* [ ] Criar tratamento específico para indisponibilidade do WFS
* [ ] Implementar controle de histórico das alterações
* [ ] Disponibilizar execução via Docker
* [ ] Criar pipeline de CI/CD

---

> **Atualizador WFS — INCRA Glebas Remanescentes**
> Automação de dados geoespaciais com Python, WFS e PostgreSQL/PostGIS.
