$ErrorActionPreference = "Stop"
Remove-Item Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY,Env:http_proxy,Env:https_proxy,Env:all_proxy -ErrorAction SilentlyContinue
$env:PATH = "C:\Users\aaron\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;" + $env:PATH
& ".\node_modules\.bin\eas.CMD" update --branch production --message "ERP SOM Android 1.7.26 update" --non-interactive
