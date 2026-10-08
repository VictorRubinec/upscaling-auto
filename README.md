# 🤖 Gemini Upscaler RPA — Studio Kustom

Automação em **Python com Playwright** para otimização, restauração e upscaling em lote de artes e imagens de baixa resolução via interface web do **Google Gemini**, voltada para o fluxo de produção de produtos físicos personalizados em alta qualidade (**300 DPI**).

---

## 📌 Visão Geral & Arquitetura

O projeto resolve o desafio de preparar arquivos de clientes com resoluções baixas ou com artefatos de compressão para impressão física profissional. A automação envia a imagem para o Gemini Web com prompts técnicos especializados por perfil de produto, aguarda a geração da IA e extrai a imagem resultante em resolução máxima nativa.

```mermaid
flowchart LR
    A["data/input/<produto>"] --> B["Validador & Idempotência (main.py)"]
    B --> C["Sessão do Navegador (Google Chrome)"]
    C --> D["Gemini Web (Upload Ctrl+V + Prompt Especializado)"]
    D --> E["Extração Direta do Modelo / Download"]
    E --> F["data/output/<produto> (*_upscaled_300dpi.png)"]
```

---

## 🎯 Perfis de Produtos Suportados

A aplicação possui configurações dimensionais e prompts de IA especializados para cada categoria de produto:

| Perfil (`--product`) | Nome de Exibição | Dimensões Finais | Foco do Prompt de IA |
| :--- | :--- | :--- | :--- |
| **`POSTER_A4`** | Pôster Formato A4 (Vertical) | 210 x 297 mm | Fidelidade de cores, remoção de ruído JPEG e nitidez vertical 210x297mm. |
| **`POSTER_A4_HORIZONTAL`** | Pôster Formato A4 (Horizontal) | 297 x 210 mm | Fidelidade de cores, remoção de ruído e manutenção estrita de formato paisagem 297x210mm. |
| **`POSTER_A3`** | Pôster Formato A3 (Vertical) | 297 x 420 mm | Super-resolução para grande escala, microdetalhes e eliminação de banding em formato vertical. |
| **`POSTER_A3_HORIZONTAL`** | Pôster Formato A3 (Horizontal) | 420 x 297 mm | Super-resolução para grande escala e microdetalhes em formato paisagem 420x297mm. |
| **`TRADING_CARD`** | Trading Card Colecionável | 63.5 x 88.9 mm | Nitidez extrema de tipografia pequena, bordas vetoriais e contraste de símbolos e frames. |
| **`POKEMON_CARD`** | Carta Pokémon Personalizada | 63.5 x 88.9 mm | Anatomia oficial TCG, fontes Gill Sans/Futura, ícones elementares e layout milimétrico a 300 DPI. |
| **`POLAROID`** | Foto Estilo Polaroid | 88 x 107 mm | Preservação de textura fotográfica natural, tons de pele e filme orgânico sem suavização excessiva. |
| **`MUG`** | Caneca Cerâmica (Panorâmica) | 200 x 95 mm (~2:1) | Preservação da proporção sem estiramento anamórfico e saturação otimizada para sublimação térmica. |

---

## 🛡️ Principais Recursos

- **Organização por Subpastas de Pedidos/Clientes**: Permite organizar os arquivos em subpastas dentro de `data/input/<produto>/` (ex: `Pedido_101/arte.jpg`, `Pedido_102/arte.jpg`). A automação espelha exatamente a mesma estrutura de diretórios em `data/output/<produto>/Pedido_101/` e cria as pastas automaticamente, evitando conflito de arquivos de mesmo nome entre pedidos diferentes.
- **Detecção Inteligente de Orientação**: O robô inspeciona as dimensões da imagem de entrada. Se você colocar uma imagem horizontal na pasta de pôster, o prompt e as medidas em mm são ajustados dinamicamente para landscape (297x210mm ou 420x297mm), instruindo o Gemini a não girar ou cortar.
- **Conexão Direta ao Chrome (CDP)**: Suporte a Chrome DevTools Protocol na porta `9222` com um perfil **isolado** (`data/browser_profile/`), sem interferir no navegador que você usa no dia a dia (login do Google feito uma única vez).
- **Upload Ágil via Clipboard (Ctrl+C / Ctrl+V)**: Injeta a imagem diretamente na caixa de chat como anexo sem depender de seletores instáveis de explorador de arquivos.
- **Isolamento de Contexto**: A cada imagem processada, aciona um novo chat limpo para evitar contaminação do histórico e estouro de janela de tokens.
- **Idempotência Inteligente**: Ignora automaticamente imagens que já possuem a versão correspondente gerada em `data/output/`, avaliando individualmente cada subpasta.
- **Extração de Imagem do Modelo**: Filtra especificamente a resposta gerada pela IA, ignorando miniaturas da mensagem do usuário e extraindo os dados em alta velocidade.
- **Observabilidade**: Logs detalhados em tempo real no console e registrados em `data/logs/automation.log`.

---

## 📂 Estrutura de Diretórios e Suporte a Subpastas

Você pode colocar as imagens diretamente na raiz do produto ou separadas por subpastas (ex: pedidos, clientes ou datas):

```text
upscaling-auto/
├── data/
│   ├── browser_profile/          # Perfil de sessão persistente
│   ├── logs/                     # Registros de log (automation.log)
│   ├── input/                    # Imagens de entrada por produto
│   │   ├── poster_a3_horizontal/
│   │   │   ├── Pedido_101/       # 📁 Subpastas suportadas livremente
│   │   │   │   └── arte.jpg
│   │   │   ├── Pedido_102/
│   │   │   │   └── arte.jpg      # Mesmo nome, sem conflito!
│   │   │   └── foto_direta.jpg   # Arquivo na raiz
│   │   ├── poster_a4/
│   │   ├── trading_card/
│   │   ├── polaroid/
│   │   └── mug/
│   └── output/                   # Imagens aprimoradas geradas (300 DPI)
│       ├── poster_a3_horizontal/
│       │   ├── Pedido_101/       # 📁 Mesma pasta espelhada automaticamente
│       │   │   └── arte_upscaled_300dpi.png
│       │   ├── Pedido_102/
│       │   │   └── arte_upscaled_300dpi.png
│       │   └── foto_direta_upscaled_300dpi.png
├── src/
│   ├── __init__.py
│   ├── config.py                 # Enums, Pydantic Models, detecção do Chrome e Prompts
│   ├── selectors.py              # Mapeamento centralizado de seletores DOM
│   ├── upscaler.py               # Motor de automação RPA Playwright
│   └── utils.py                  # Logger, verificação CDP, retry e clipboard
├── iniciar_chrome.bat            # Script para abrir o Chrome de automação (porta 9222, perfil isolado)
├── init_session.py               # Script para login manual inicial
├── main.py                       # CLI principal de processamento em lote
├── requirements.txt              # Dependências do projeto
└── README.md
```

---

## ⚙️ Instalação e Pré-requisitos

### 1. Clonar o Repositório
```bash
git clone https://github.com/VictorRubinec/upscaling-auto.git
cd upscaling-auto
```

### 2. Instalar as Dependências
Recomenda-se o uso do Python 3.10 ou superior:

```bash
# Criar e ativar ambiente virtual (opcional)
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Instalar navegadores do Playwright (se necessário)
playwright install chromium
```

---

## 🚀 Como Executar

### 1. Iniciar o Navegador (Google Chrome de automação)
O Chrome de automação usa um perfil próprio em `data/browser_profile/`, então **não é preciso fechar** o seu navegador do dia a dia (Brave ou outro):

1. Na primeira vez, execute o arquivo [`iniciar_chrome.bat`](iniciar_chrome.bat) e faça login na conta Google na janela aberta (o login fica salvo no perfil).
2. Nas próximas, execute o arquivo (ou rode no terminal):
   ```powershell
   .\iniciar_chrome.bat
   ```
   *(O Chrome abrirá na página do Gemini com a porta de automação habilitada). Se preferir, rode apenas `python main.py ...` e o Chrome é aberto automaticamente com o mesmo perfil.*

### 2. Adicionar Imagens de Entrada
Coloque as imagens (`.png`, `.jpg`, `.jpeg`, `.webp`) dentro da pasta correspondente em `data/input/<produto>/`.

### 3. Disparar a Automação

#### Processar um produto específico:
```powershell
# Pôster A4 Vertical (ou auto-detectado caso a imagem seja horizontal)
python main.py --product POSTER_A4

# Pôster A4 Horizontal dedicado (297x210 mm)
python main.py --product POSTER_A4_HORIZONTAL

# Pôster A3 Vertical
python main.py --product POSTER_A3

# Pôster A3 Horizontal dedicado (420x297 mm)
python main.py --product POSTER_A3_HORIZONTAL

# Forçar orientação (auto | vertical | horizontal)
python main.py --product POSTER_A4 --orientation horizontal

# Trading Cards
python main.py --product TRADING_CARD

# Fotos Polaroid
python main.py --product POLAROID

# Canecas (Mug)
python main.py --product MUG
```

#### Processar todos os produtos com arquivos pendentes:
```powershell
python main.py --all
```

#### Argumentos Adicionais:
* `--orientation, -o {auto,vertical,horizontal}`: Define a orientação física do pôster (padrão: `auto` que detecta dinamicamente a largura/altura da imagem de entrada e formata as dimensões em milímetros correspondentes).
* `--headless`: Executa o navegador sem abrir janela visual.
* `--timeout <ms>`: Define o tempo limite por imagem em milissegundos (padrão: `180000` = 3 minutos).

---

## 📄 Licença

Projeto desenvolvido para uso interno da **Studio Kustom**.
