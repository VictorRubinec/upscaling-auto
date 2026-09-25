class GeminiSelectors:
    """Mapeamento e centralização de seletores DOM da interface Web do Google Gemini."""

    # Campo de digitação de prompt
    PROMPT_INPUT = (
        "div[contenteditable='true'].ql-editor, "
        "div.ql-editor[role='textbox'], "
        "rich-textarea p, "
        "rich-textarea div[contenteditable='true'], "
        "textarea[aria-label*='Prompt'], "
        "div[aria-label*='Insira uma instrução'], "
        "div[aria-label*='Enter a prompt'], "
        "div[aria-label*='Pergunte ao Gemini'], "
        "div[aria-label*='Ask Gemini'], "
        "div[role='textbox']"
    )

    # Input oculto para upload direto de arquivos
    FILE_INPUT = "input[type='file']"

    # Botão de anexar imagem/arquivo (+ ou ícone de clipe/upload)
    ATTACH_BUTTON = (
        "button[aria-label*='upload' i], "
        "button[aria-label*='Adicionar' i], "
        "button[aria-label*='Inserir' i], "
        "button[aria-label*='Attach' i], "
        "button[aria-label*='Abrir menu' i], "
        "button.uploader-button, "
        "button[data-test-id='attachment-menu-button'], "
        "button[data-test-id*='upload'], "
        "button:has(mat-icon:has-text('add')), "
        "button:has(mat-icon:has-text('attach_file')), "
        "button:has(mat-icon:has-text('upload'))"
    )

    # Itens de menu popup de upload
    UPLOAD_MENU_ITEM = (
        "button[role='menuitem']:has-text('Fazer upload'), "
        "button[role='menuitem']:has-text('Upload'), "
        "button[role='menuitem']:has-text('computador'), "
        "button[role='menuitem']:has-text('arquivos'), "
        "div[role='menuitem']:has-text('Upload'), "
        "div[role='menuitem']:has-text('computador')"
    )

    # Botão de envio de mensagem
    SEND_BUTTON = (
        "button.send-button, "
        "button[aria-label*='Enviar' i], "
        "button[aria-label*='Send' i], "
        "button[aria-label*='Submit' i], "
        "button[data-test-id='send-button'], "
        "button:has(mat-icon:has-text('send'))"
    )

    # Indicadores visuais de que o Gemini está processando/gerando resposta
    GENERATING_INDICATOR = (
        "div.sparkle-container, "
        "mat-progress-bar, "
        "[data-test-id='generating-state'], "
        ".loading-indicator, "
        "div[aria-label*='Gerando' i], "
        "div[aria-label*='Thinking' i], "
        "div[aria-label*='Pensando' i]"
    )

    # Elementos de imagem gerada nas respostas
    GENERATED_IMAGE = (
        "div.model-response-text img, "
        "image-viewer img, "
        ".response-container img, "
        "message-content img, "
        "generated-image img, "
        "img[src*='googleusercontent.com'], "
        "img[src*='blob:']"
    )

    # Botão para download da imagem em tamanho completo
    DOWNLOAD_BUTTON = (
        "button[aria-label*='Fazer o download' i], "
        "button[aria-label*='Download' i], "
        "button[aria-label*='tamanho original' i], "
        "button[aria-label*='Baixar' i], "
        "a[download], "
        "button:has(mat-icon:has-text('download'))"
    )

    # Botão de início de novo chat
    NEW_CHAT_BUTTON = (
        "a[aria-label*='Novo chat' i], "
        "button[aria-label*='Novo chat' i], "
        "button[aria-label*='New chat' i], "
        "[data-test-id='new-chat-button'], "
        "a[href='/app'], "
        "a:has-text('Novo chat')"
    )

    # Botões para fechar eventuais modais/popups de avisos
    MODAL_DISMISS_BUTTON = (
        "button[aria-label*='Fechar' i], "
        "button[aria-label*='Close' i], "
        "button[aria-label*='Dismiss' i], "
        "button:has-text('Entendi'), "
        "button:has-text('Got it'), "
        "button:has-text('Continuar'), "
        "button:has-text('Aceitar')"
    )
