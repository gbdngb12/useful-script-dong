```bash
make defconfig
make kvm_guest.config
make menuconfig # ENABLE Debugging info, gdb python script
make -j `nproc`
```

`run.sh`

```
#!/bin/bash
export KERNEL="/root/kernel_debug/linux-5.10.11"
export IMAGE="/root/kernel_debug/image"
qemu-system-x86_64 \
-enable-kvm \
-m 2G \
-smp 2 \
-kernel $KERNEL/arch/x86/boot/bzImage \
-append "root=/dev/vda1 console=tty1 console=ttyS0 nokaslr earlyprintk=serial net.ifnames=0" \
-drive if=virtio,format=qcow2,file=$IMAGE/ubuntu-22.04-minimal-cloudimg-amd64.img \
-drive if=virtio,format=raw,file=$IMAGE/seed.raw \
-net user,host=10.0.2.10,hostfwd=tcp:127.0.0.1:10021-:22 \
-net nic,model=e1000 \
-nographic \
-S -s
```

```
gdb vmlinux
(gdb) dir $linux_source_dir
(gdb) source ./vmlinux-gdb.py
(gdb) target remote :1234
```
