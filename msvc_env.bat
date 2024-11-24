@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat"


#!/bin/bash
vmrun -T ws start /home/dong/vmware/lsw/lsw.vmx nogui
sshpass -p dong ssh dong@192.168.159.130
