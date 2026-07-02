@echo off
title Infranodus MCP HTTP Server (port 8789)
"C:\nvm4w\nodejs\node.exe" "C:\Users\user1\AppData\Roaming\npm\node_modules\supergateway\dist\index.js" --stdio "npx -y infranodus-mcp-server" --port 8789 --ssePath /mcp
