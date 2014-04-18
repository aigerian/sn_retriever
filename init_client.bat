reg add "hklm\software\microsoft\windows\currentversion\run" /v "sn_client" /t reg_sz /d %~dp0client.exe /f 
client.exe
