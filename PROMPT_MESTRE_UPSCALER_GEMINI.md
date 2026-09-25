# 🤖 PROMPT MESTRE DE DESENVOLVIMENTO: ROBÔ RPA DE UPSCALING EM LOTE VIA GEMINI PRO WEB

Atue como um **Engenheiro de Automação Sênior (Especialista em RPA, Python e Playwright)** e **Arquiteto de Software**. Sua missão é construir do zero uma aplicação completa, robusta, altamente tipada e resiliente para **upscaling e aprimoramento de imagens em lote via interface web do Google Gemini Pro**, voltada para o fluxo de produção de produtos físicos personalizados em alta resolução (300 DPI).

---

## 1. 🎯 OBJETIVO E ESCOPO DO PROJETO

Construir uma ferramenta RPA em Python 3.10+ utilizando **Playwright** que:
1. **Reutiliza uma Sessão Persistente** (cookies, autenticação Google, 2FA e cache) armazenada em disco para não exigir login recorrente.
2. **Varre Diretórios de Entrada por Perfil de Produto Físico**, detectando arquivos de imagem (`.png`, `.jpg`, `.jpeg`, `.webp`).
3. **Aplica Idempotência Estrita**: ignora automaticamente arquivos que já possuam a imagem de saída correspondente gerada.
4. **Interage com o Gemini Web**:
   - Inicia ou limpa o contexto do chat para evitar poluição de histórico.
   - Faz upload do arquivo da imagem.
   - Injeta o prompt técnico especializado e otimizado para o perfil de produto selecionado.
   - Dispara a mensagem e monitora ativamente o ciclo de processamento da IA.
   - Baixa a imagem gerada na **resolução máxima nativa**.
5. **Salva a Imagem no Diretório de Saída com Sufixo Padronizado** (ex: `{nome_original}_upscaled_300dpi.png`).
6. **Oferece Observabilidade e Resiliência**: logs estruturados em arquivo e console, tratamento de timeouts, retentativas automáticas e tratamento de erros dinâmicos no DOM.

---

## 2. 🛠️ STACK TECNOLÓGICA E DEPENDÊNCIAS

- **Linguagem**: Python 3.10+
- **Automação Web / Navegador**: `playwright` (Chromium / Google Chrome nativo)
- **Modelagem e Validação de Dados**: `pydantic >= 2.0`
- **Requisições e Fallback de Download**: `requests`
- **CLI e Terminal**: `argparse` / `typer`
- **Logging e Observabilidade**: módulo nativo `logging` estruturado com rotação de arquivos

```text
# requirements.txt
playwright>=1.40.0
pydantic>=2.5.0
requests>=2.31.0
```

---

## 3. 📐 ARQUITETURA E ESTRUTURA DE DIRETÓRIOS

Você deve gerar rigorosamente a seguinte topologia de arquivos e pastas:

```text
gemini-upscaler-rpa/
├── data/
│   ├── browser_profile/          # Perfil persistente do Chrome (Sessão Google/Gemini)
│   ├── logs/                     # Arquivos de log gerados pela aplicação
│   ├── input/                    # Pastas de entrada por produto
│   │   ├── poster_a4/
│   │   ├── poster_a3/
│   │   ├── trading_card/
│   │   ├── polaroid/
│   │   └── mug/
│   └── output/                   # Pastas de saída com artes aprimoradas
│       ├── poster_a4/
│       ├── poster_a3/
│       ├── trading_card/
│       ├── polaroid/
│       └── mug/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Enums, Pydantic Models e Catálogo de Produtos/Prompts
│   ├── selectors.py              # Centralização de seletores DOM do Gemini Web
│   ├── upscaler.py               # Motor de automação RPA (Upload, Prompt, Monitoramento e Download)
│   └── utils.py                  # Decorator de retry, setup de logging e sanitização
├── init_session.py               # Script CLI para autenticação inicial do usuário
├── main.py                       # CLI principal para disparo dos lotes por produto
├── requirements.txt
└── README.md
```

---

## 4. 🧩 ESPECIFICAÇÃO DETALHADA DOS MÓDULOS

### Módulo 1: `src/config.py` (Tipagem e Catálogo de Perfis)
- Defina o `Enum` `ProductType` com os valores: `POSTER_A4`, `POSTER_A3`, `TRADING_CARD`, `POLAROID`, `MUG`.
- Crie o modelo Pydantic `ProductProfile` encapsulando:
  - `product_type: ProductType`
  - `display_name: str`
  - `target_dimensions_mm: Tuple[float, float]`
  - `target_dpi: int = 300`
  - `aspect_ratio: str`
  - `system_prompt: str` (Prompt de IA especializado no tipo de impressão)
  - `output_suffix: str = "_upscaled_300dpi"`
  - `input_subpath: str`
  - `output_subpath: str`
  - Métodos utilitários `get_input_dir(base_data_dir: Path) -> Path` e `get_output_dir(base_data_dir: Path) -> Path` com criação automática de diretórios (`mkdir(parents=True, exist_ok=True)`).
- Implemente o dicionário `PRODUCT_REGISTRY: Dict[ProductType, ProductProfile]` com os prompts técnicos específicos:
  - **`POSTER_A4` (210x297 mm)**: Foco em remoção de ruído JPEG, fidelidade de cor e nitidez equilibrada.
  - **`POSTER_A3` (297x420 mm)**: Foco em super-resolução para grande formato, reconstrução de microdetalhes e eliminação de artefatos de gradiente.
  - **`TRADING_CARD` (63.5x88.9 mm)**: Foco em nitidez de tipografia pequena, legibilidade de textos de cards e contornos vetoriais.
  - **`POLAROID` (88x107 mm)**: Foco em preservação de tom de pele e textura fotográfica natural.
  - **`MUG` (200x95 mm)**: Foco em formato panorâmico sem distorção anamórfica e vivacidade para sublimação.
- Crie o modelo `AppSettings` contendo:
  - Caminhos base (`base_dir`, `data_dir`, `user_data_dir`).
  - `gemini_url: str = "https://gemini.google.com/app"`.
  - `headless: bool = False` (configurável).
  - `timeout_ms: int = 180000` (3 minutos para espera de renderização).
  - `max_retries: int = 3`.
  - `delay_between_files_sec: float = 4.0`.
  - `supported_extensions: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")`.

---

### Módulo 2: `src/selectors.py` (Mapeamento DOM)
Centralize todos os seletores CSS e XPath em uma classe `GeminiSelectors`:
- `PROMPT_INPUT`: `div[contenteditable='true'].ql-editor, div.ql-editor[role='textbox'], rich-textarea p`
- `FILE_INPUT`: `input[type='file']`
- `ATTACH_BUTTON`: `button[aria-label*='upload'], button[aria-label*='Adicionar arquivos'], button[aria-label*='Attach']`
- `SEND_BUTTON`: `button.send-button, button[aria-label*='Enviar'], button[aria-label*='Send message']`
- `GENERATING_INDICATOR`: `div.sparkle-container, mat-progress-bar, [data-test-id='generating-state']`
- `GENERATED_IMAGE`: `div.model-response-text img, image-viewer img, .response-container img`
- `DOWNLOAD_BUTTON`: `button[aria-label*='Fazer o download'], button[aria-label*='Download full size'], a[download]`
- `NEW_CHAT_BUTTON`: `a[aria-label*='Novo chat'], button[aria-label*='New chat']`

---

### Módulo 3: `src/utils.py` (Observabilidade e Retries)
- `setup_logger(log_file: Path) -> logging.Logger`: Criação de logger com formatação padronizada `[DATA HORA] [NIVEL] [NOME]: Mensagem` gravando no console (`sys.stdout`) e em arquivo `data/logs/automation.log`.
- `@retry(max_attempts=3, delay_sec=3.0)`: Decorator resiliente que captura exceções, emite aviso no log e retenta a execução.

---

### Módulo 4: `src/upscaler.py` (Motor de Automação do Playwright)
Classe `GeminiUpscalerEngine`:
- Recebe `context: BrowserContext` e `settings: AppSettings`.
- Método `ensure_chat_ready()`: Valida se está na URL do Gemini e clica em `NEW_CHAT_BUTTON` para manter a sessão limpa.
- Método `process_single_image(image_path: Path, profile: ProductProfile) -> Path`:
  1. Identifica o caminho de saída `{image_path.stem}{profile.output_suffix}.png`.
  2. Faz o upload da imagem via `set_input_files` no seletor de arquivo ou via listener de file chooser.
  3. Preenche a caixa de texto com o prompt especializado do perfil de produto.
  4. Clica no botão de envio ou pressiona Enter.
  5. Aguarda a imagem gerada com timeout customizável.
  6. Realiza o download através do evento `expect_download` ou fallback via stream HTTP autenticado com os cookies da sessão.
  7. Salva o arquivo no diretório final de saída.

---

### Módulo 5: `init_session.py` (Inicializador de Sessão)
- Script interativo que executa o Playwright com `launch_persistent_context(user_data_dir=...)` em modo visível (`headless=False`), navega até `https://gemini.google.com/app` e aguarda o usuário fazer o login e pressionar ENTER no terminal para consolidar a sessão.

---

### Módulo 6: `main.py` (CLI e Orquestrador em Lote)
- Configura argumentos CLI com `argparse` (`--product`).
- Valida idempotência antes de iniciar o navegador (ignora imagens que já possuem saída gerada).
- Abre o contexto do Playwright com flags anti-detecção (`--disable-blink-features=AutomationControlled`, `--start-maximized`).
- Itera sobre o lote de imagens, reportando contagem de progresso `[X/Total]`, sucessos e erros.
- Fecha o contexto com segurança e emite o resumo final.

---

## 5. ⚡ REQUISITOS NÃO-FUNCIONAIS E BOAS PRÁTICAS

1. **Anti-Detecção e Persistência**: Utilize sempre `launch_persistent_context` apontando para a pasta `data/browser_profile/` com o canal nativo do Google Chrome (`channel="chrome"`).
2. **Manipulação de Exceções**: Se um arquivo falhar, o script deve registrar o log de erro com traceback completo, mas **não deve interromper a execução do lote**, continuando para a próxima imagem.
3. **Limpeza de Contexto**: A cada imagem processada, acione um novo chat para evitar extrapolar a janela de contexto de tokens do Gemini.
4. **Tipagem Estrita**: Todos os métodos devem ter type hints explícitos (`Path`, `Tuple`, `Optional`, `Dict`, etc.).

---

## 🚀 CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Criar estrutura de pastas (`data/`, `src/`, etc.).
- [ ] Criar `requirements.txt` com `playwright`, `pydantic` e `requests`.
- [ ] Implementar `src/config.py` com `ProductType`, `ProductProfile` e `PRODUCT_REGISTRY`.
- [ ] Implementar `src/selectors.py` com seletores robustos e com múltiplos fallbacks.
- [ ] Implementar `src/utils.py` com logging e decorator de retry.
- [ ] Implementar `src/upscaler.py` com tratamento de upload, download e erros de timeout.
- [ ] Implementar `init_session.py` para autenticação inicial e armazenamento da sessão.
- [ ] Implementar `main.py` com CLI, filtro de idempotência e relatório final de lote.
- [ ] Criar `README.md` explicativo com o passo a passo de inicialização e execução.
