$node = "C:\nvm4w\nodejs\node.exe"
$sg = "C:\Users\user1\AppData\Roaming\npm\node_modules\supergateway\dist\index.js"
$fs = "C:\Users\user1\AppData\Local\npm-cache\_npx\a3241bba59c344f5\node_modules\.bin\..\@modelcontextprotocol\server-filesystem\dist\index.js"
$vault = "C:\ObsidianVaultLink"
$stdioCmd = "$node `"$fs`" `"$vault`""
& $node $sg --stdio $stdioCmd --port 8788 --ssePath /sse
