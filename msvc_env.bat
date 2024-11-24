@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat"


#!/bin/bash
vmrun -T ws start /home/dong/vmware/lsw/lsw.vmx nogui
sshpass -p dong ssh dong@192.168.159.130



bcdedit /debug on
bcdedit /dbgsettings net hostip:192.168.139.129 port:50000

debugger에서는 Key값 넣어주기
