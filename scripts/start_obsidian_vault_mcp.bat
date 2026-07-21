@echo off
title ObsidianVault MCP HTTP Server (port 8788)
"C:\nvm4w\nodejs\node.exe" "C:\Users\user1\AppData\Roaming\npm\node_modules\supergateway\dist\index.js" --stdio "npx -y @modelcontextprotocol/server-filesystem \"D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\"" --port 8788 --ssePath /mcp
