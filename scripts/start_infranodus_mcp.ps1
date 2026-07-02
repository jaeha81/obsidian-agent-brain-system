$node = "C:\nvm4w\nodejs\node.exe"
$sg = "C:\Users\user1\AppData\Roaming\npm\node_modules\supergateway\dist\index.js"
$infra = "C:\Users\user1\AppData\Local\npm-cache\_npx\ec928b7542a95fad\node_modules\.bin\..\infranodus-mcp-server\bin\infranodus-mcp-server.js"
$stdioCmd = "$node `"$infra`""
& $node $sg --stdio $stdioCmd --port 8789 --ssePath /sse
