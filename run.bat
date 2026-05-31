@echo off
REM Launches a local HTTP server in this folder so the swatch tools can
REM fetch ICC LUTs + JSON. Opens the zen landing page in the default browser.
REM Close this window to stop the server.

cd /d "%~dp0"
echo Starting local server at http://localhost:8765 ...
echo.
echo  Landing:       http://localhost:8765/
echo  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html
echo  3D explorer:   http://localhost:8765/app/3d-explorer.html
echo.
echo Close this window to stop the server.
echo.
start "" "http://localhost:8765/"
python -m http.server 8765
