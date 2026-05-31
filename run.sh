#!/usr/bin/env bash
# Launches a local HTTP server in this folder so the swatch tools can
# fetch ICC LUTs + JSON. Opens the zen landing page in the default browser.
cd "$(dirname "$0")"
echo "Starting local server at http://localhost:8765 ..."
echo
echo "  Landing:       http://localhost:8765/"
echo "  CMYK explorer: http://localhost:8765/app/cmyk-explorer.html"
echo "  3D explorer:   http://localhost:8765/app/3d-explorer.html"
echo
echo "Ctrl+C to stop."
echo

if   command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:8765/" >/dev/null 2>&1
elif command -v open      >/dev/null 2>&1; then open      "http://localhost:8765/" >/dev/null 2>&1
fi
exec python -m http.server 8765
