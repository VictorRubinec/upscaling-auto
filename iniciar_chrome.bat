@echo off
chcp 65001 > nul
echo ======================================================================
echo    Iniciando Google Chrome de AUTOMACAO (Porta 9222, perfil isolado)
echo ======================================================================
echo.
echo Este Chrome usa um perfil proprio em data\browser_profile e NAO interfere
echo com o seu navegador do dia a dia (Brave ou outro) nem com o Chrome normal.
echo Nenhum processo sera encerrado.
echo.

set "PROFILE_DIR=%~dp0data\browser_profile"
set "CHROME_EXE="

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not defined CHROME_EXE (
    echo [ERRO] Executavel do Google Chrome nao foi encontrado nas pastas padrao.
    goto :end
)

echo Abrindo o Chrome diretamente no Google Gemini...
start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check "https://gemini.google.com/app"
echo.
echo ✅ Chrome iniciado! Se for a primeira vez, faca login na conta Google nesta janela
echo    (o login fica salvo em data\browser_profile).

:end
echo.
echo Agora execute no terminal: python main.py --all
echo.
