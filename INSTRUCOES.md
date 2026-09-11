# Como instalar a atualização automática via GitHub Actions

Isso substitui a tarefa agendada do Claude: o dashboard passa a se atualizar sozinho todo dia às 08:05, rodando nos servidores do GitHub — sem depender do Windows.

## 1. Adicionar 3 arquivos ao repositório `RennanMendonca/dashboard-microchipagem`

Pelo site do GitHub (Add file → Upload files), envie para a **raiz** do repositório:

- `build.py`
- `validate_html.py`
- `votacao_master.json`

E crie a pasta `.github/workflows/` com o arquivo `update-dashboard.yml` dentro dela (no GitHub, ao criar um novo arquivo, você pode digitar o caminho completo `.github/workflows/update-dashboard.yml` no campo de nome que ele cria a pasta automaticamente).

O `template.html` que já está no repo não precisa mudar.

## 2. Cadastrar o token da API como "secret"

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

- Nome: `DEMANDASRIO_TOKEN`
- Valor: `fb8d2c084adbd2d741a42379930e5d45`

Esse token nunca aparece no código nem no HTML publicado — fica só nesse cofre do GitHub.

## 3. Dar permissão de escrita para o Actions

**Settings → Actions → General → Workflow permissions** → marque **"Read and write permissions"** → Save.

Sem isso o workflow gera o dashboard mas não consegue commitar o resultado de volta no repo.

## 4. Testar

Vá em **Actions → Atualiza Dashboard Microchipagem → Run workflow** para rodar uma vez manualmente e conferir que funciona. Depois disso ele roda sozinho todo dia às 08:05 (Brasília).

## 5. Desativar a tarefa agendada antiga no Claude (opcional)

Como o GitHub Actions assume a atualização diária, você pode desativar ou apagar a tarefa `dashboard-microchipagem-update` agendada aqui no Claude, para não ficar duplicado. Posso fazer isso pra você se quiser.
