@echo off
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Installing Playwright browser (Chromium)...
playwright install chromium

echo.
echo Setup complete!
echo Next steps:
echo   1. Open .env and fill in your Facebook and Telegram credentials
echo   2. Run the bot with:  run.bat
pause
