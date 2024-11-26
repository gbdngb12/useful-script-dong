## Debuggee
```bash
bcdedit /debug on
bcdedit /dbgsettings net hostip:192.168.139.129 port:50000
```
## Debugger
```
kd.exe -k net:port=50000,key="3fxtk90pm6ito.127qdoxjan38n.1u9pcj4o7ldzt.4ryk1ihfxpgf"
```
debugger에서는 Key값 넣어주기
