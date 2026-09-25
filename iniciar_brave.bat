@echo off
chcp 65001 > nul
echo ======================================================================
echo    Iniciando Brave Browser com suporte a automacao (Porta 9222)
echo ======================================================================
echo.
echo Fechando processos em segundo plano do Brave para aplicar a porta 9222...
taskkill /F /IM brave.exe 2>nul
timeout /t 1 /nobreak >nul

echo Abrindo o Brave diretamente no Google Gemini...
if exist "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" (
    start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222 "https://gemini.google.com/app"
    echo.
    echo ✅ Brave iniciado com sucesso com seu perfil e login!
) else if exist "C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe" (
    start "" "C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222 "https://gemini.google.com/app"
    echo.
    echo ✅ Brave iniciado com sucesso com seu perfil e login!
) else (
    echo [ERRO] Executavel do Brave nao foi encontrado nas pastas padrao.
)

echo.
echo Agora execute no terminal: python main.py --all
echo.
