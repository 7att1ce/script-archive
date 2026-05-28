# Arch Linux installation record

## Device

- Laptop: ASUS TUFGaming A16 2024 FA607PV
- CPU: AMD Ryzen R9-7940HX
- Memory: DDR5 5200MHZ 32GB
- GPU: NVIDIA RTX 4060 Laptop
- Disk:
  - WD PC SN560 SDDPNQE-1T00-1102 1TB
  - KIOXIA-EXCERIA PLUS G3 SSD 1TB

## References

- [https://asus-linux.org/guides/arch-guide/](https://asus-linux.org/guides/arch-guide/)
- [https://wiki.archlinux.org/title/Installation_guide](https://wiki.archlinux.org/title/Installation_guide)

## Preinstallation

1. 下载 Arch Linux ISO, 准备安装媒介 (USB 安装, PXE 安装, 等等).
2. 进入 BIOS 页面
  - 开启 Erp
  - 关闭 Armoury Crate 控制接口支持
  - 显示模式设置为动态
  - 关闭 AMD 超频
  - 关闭快速启动
  - 关闭安全启动
3. 电脑启动到 Arch Linux 安装环境

## Steps

### 1. 连接到互联网

对于有线网络, 一般插上网线就会自动通过 DHCP 连接网络, 这里暂时没有分配静态 IP 需求, 暂且跳过  
对于无线网络, 使用 `iwctl` 进行连接

> 使用 `iwctl` 连接无线网络步骤:  
> 参考: [https://wiki.archlinux.org/title/Iwd#iwctl](https://wiki.archlinux.org/title/Iwd#iwctl)  
> 查看无线网卡设备并确保已开启
> ```shell
> iwctl device list
> ```
> 扫描并查看可用网络 (wlan0 应当被更改为具体的设备名, 之后同理)
> ```shell
> iwctl station wlan0 scan
> iwctl station wlan0 get-networks
> ```
> 连接网络 (SSID 为具体的无线网络名称, 如果提示输入密码直接输入即可)
> ```shell
> iwctl station wlan0 connect SSID
> ```

检查互联网连接
```shell
ping ping.archlinux.org
```

### 2. 更新系统时钟

确保系统时钟同步
```shell
timedatectl
```

### 3. 磁盘分区

查看要安装系统的磁盘设备 (由于设备较多, 使用 `less` 命令方便滚动屏幕)
```shell
fdisk -l | less
```
这里要将系统安装在移动硬盘 (Extreme 55AE) 上, 对应的设备应该是 `/dev/sda`  
硬盘分区
```shell
cfdisk /dev/sda
```
分区类型选 GPT  
分区方案:
|Mount Point|Partition     |Partition type GUID                                        |Size     |
|:---------:|:------------:|:---------------------------------------------------------:|:-------:|
|/boot      |/dev/sda1|`C12A7328-F81F-11D2-BA4B-00A0C93EC93B`: EFI System         |1GB      |
|\[SWAP\]   |/dev/sda2|`0657FD6D-A4AB-43C4-84E5-0933C84B4F4F`: Linux swap         |32GB     |
|/          |/dev/sda3|`4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709`: Linux root (x86-64)|Remainder|

查看分区更改
```shell
fdisk -l /dev/sda
```

### 4. 格式化分区

```shell
mkfs.fat -F 32 /dev/sda1
mkswap /dev/sda2
mkfs.ext4 /dev/sda3
```
检查格式化
```shell
lsblk -f /dev/sda
```

### 5. 挂载文件系统

```shell
mount /dev/sda3 /mnt
mount --mkdir /dev/sda1 /mnt/boot
swapon /dev/sda2
```

### 6. 修改镜像源

```shell
cp /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist.bak

# nano /etc/pacman.d/mirrorlist # 编辑 /etc/pacman.d/mirrorlist, 将 CN 镜像源移动到顶部
# 一种替换方案
curl -L 'https://archlinux.org/mirrorlist/?country=CN&protocol=https' -o /etc/pacman.d/mirrorlist
nano /etc/pacman.d/mirrorlist # 去掉注释
```

### 7. 安装基础包
 
安装内容简介:
- base, base-devel, linux, linux-firmware: 基础包, 包含基础内核, 固件, 应用程序. base-devel 是后面安装nvidia-laptop-power-cfg 中 makepkg 的依赖
- amd-ucode: AMD CPU 微码
- networkmanager, modemmanager, usb_modeswitch: 网络管理, 后两者为 PPPoE 上网需要 (其实可以不安装)
- nano, vi, vim: 文本编辑器, 其中 vi 是 visudo 的默认编辑器, 如果不安装的话须额外配置全局默认编辑器
- man-db, man-pages, texinfo: 命令帮助手册
- sudo: 以非 root 用户身份执行特权命令
- bluez, bluez-utils: 蓝牙相关
- wget, git, openssh: 顾名思义

```shell
pacstrap -K /mnt base base-devel linux linux-firmware amd-ucode networkmanager modemmanager usb_modeswitch nano vi vim man-db man-pages texinfo sudo bluez bluez-utils wget git openssh
```

### 8. 配置系统

```shell
genfstab -U /mnt >> /mnt/etc/fstab

arch-chroot /mnt

ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
hwclock --systohc

# 取消掉 en_US.UTF8 UTF-8 和 zh_CN.UTF-8 UTF-8 的注释
# 这里原本想取消注释 en_SG.UTF8 UTF-8 和 zh_SG.UTF-8 UTF-8, 发现 KDE 桌面语言混乱
nano /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" >> /etc/locale.conf

echo "asus" >> /etc/hostname

passwd

# 配置 systemd-boot (asus-linux.org 不推荐使用 GRUB)
bootctl install
bootctl --variables=no --graceful update
# system-boot 配置文件参考
# https://blog.yoitsu.moe/arch-linux/using_systemd_boot.html
# https://blog.wtm.moe/articles/grub2systemd-boot/
# arch.conf
# title   Arch Linux
# linux   /vmlinuz-linux
# initrd  /amd-ucode.img
# initrd  /initramfs-linux.img
# options root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw
# echo -e "title   Arch Linux\nlinux   /vmlinuz-linux\ninitrd  /amd-ucode.img\ninitrd  /initramfs-linux.img\noptions root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw" >> /boot/loader/entries/arch.conf
echo "title   Arch Linux" >> /boot/loader/entries/arch.conf
echo "linux   /vmlinuz-linux" >> /boot/loader/entries/arch.conf
echo "initrd  /amd-ucode.img" >> /boot/loader/entries/arch.conf
echo "initrd  /initramfs-linux.img" >> /boot/loader/entries/arch.conf
echo "options root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw" >> /boot/loader/entries/arch.conf
# loader.conf
# default arch.conf
# timeout 3
# echo -e "default arch.conf\ntimeout 3" >> /boot/loader/loader.conf
echo "default arch.conf" >> /boot/loader/loader.conf
echo "timeout 3" >> /boot/loader/loader.conf
bootctl update

# 与 networkmanager 冲突
# systemctl enable systemd-networkd.service
systemctl enable systemd-resolved.service
# 与 networkmanager 冲突
# systemctl enable iwd.service
systemctl enable ModemManager.service
systemctl enable bluetooth.service
# 启用 networkmanager, 注意与 systemd-networkd 和 iwd 冲突
systemctl enable NetworkManager.service

systemctl enable sshd.service

useradd -m -G wheel user
passwd user

# 取消注释 wheel 配置
visudo

exit

# 直接复制 archiso 的配置
# 不用 systemd-networkd 的话不用复制该配置
# cp /etc/systemd/network/* /mnt/etc/systemd/network/
cp /etc/pacman.d/mirrorlist.bak /mnt/etc/pacman.d/

umount -R /mnt

poweroff
```

### 9. asus-linux.org 配置

移除安装介质, 开机  
以非 root 用户登录  
添加 g14 仓库
```shell
# 根据 asus-linux 官方指定 keyserver 也无法找到对应的签名, 只能单独下载签名本地导入
wget "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x8b15a6b0e9a3fa35" -O g14.sec
sudo pacman-key -a g14.sec
sudo pacman-key --finger 8F654886F17D497FEFE3DB448B15A6B0E9A3FA35
sudo pacman-key --lsign-key 8F654886F17D497FEFE3DB448B15A6B0E9A3FA35
sudo pacman-key --finger 8F654886F17D497FEFE3DB448B15A6B0E9A3FA35
rm g14.sec

# /etc/pacman.conf 最底部添加
# [g14]
# # Germany, origin
# # Server = https://arch.asus-linux.org
# # Republic of Korea
# Server = https://naru.jhyub.dev/$repo
# sudo echo -e "\n[g14]\n#Server = https://arch.asus-linux.org\nServer = https://naru.jhyub.dev/\$repo" >> /etc/pacman.conf
sudo echo "" >> /etc/pacman.conf
sudo echo "[g14]" >> /etc/pacman.conf
sudo echo "# Germany, origin" >> /etc/pacman.conf
sudo echo "# Server = https://arch.asus-linux.org" >> /etc/pacman.conf
sudo echo "# Republic of Korea" >> /etc/pacman.conf
sudo echo "Server = https://naru.jhyub.dev/\$repo" >> /etc/pacman.conf

sudo pacman -Syu
```
安装额外组件
```shell
sudo pacman -S asusctl power-profiles-daemon
sudo systemctl enable --now power-profiles-daemon.service
sudo asusctl profile -a Quiet

sudo pacman -S rog-control-center

# no need custom kernel
# sudo pacman -S linux-g14 linux-g14-headers

reboot

# 由于针对此设备的改动已经合并到主线内核, 无需安装自定义内核, 同时 nvidia 显卡驱动应该安装 nvidia-open 而不是 nvidia-open-dkms, 待更改

# 添加 systemd-boot 配置
# arch-g14.conf
# title   Arch Linux G14
# linux   /vmlinuz-linux-g14
# initrd  /amd-ucode.img
# initrd  /initramfs-linux-g14.img
# options root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw
# sudo echo -e "title   Arch Linux G14\nlinux   /vmlinuz-linux-g14\ninitrd  /amd-ucode.img\ninitrd  /initramfs-linux-g14.img\noptions root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw" >> /boot/loader/entries/arch-g14.conf

# sudo echo "title   Arch Linux G14" >> /boot/loader/entries/arch-g14.conf
# sudo echo "linux   /vmlinuz-linux-g14" >> /boot/loader/entries/arch-g14.conf
# sudo echo "initrd  /amd-ucode.img" >> /boot/loader/entries/arch-g14.conf
# sudo echo "initrd  /initramfs-linux-g14.img" >> /boot/loader/entries/arch-g14.conf
# sudo echo "options root=PARTUUID=$(blkid -s PARTUUID -o value /dev/sda3) rw" >> /boot/loader/entries/arch-g14.conf
# 修改默认启动项为 arch-g14.conf
# sudo nano /boot/loader/loader.conf
```
安装显卡驱动

> 由于不使用自定义内核, 应安装 nvidia-open 而不是 nvidia-open-dkms, 待更改

```shell
# 取消注释 [multilib] 启用 32 位源
sudo nano /etc/pacman.conf

sudo pacman -S --needed nvidia-open nvidia-utils lib32-nvidia-utils vulkan-icd-loader lib32-vulkan-icd-loader
sudo pacman -S --needed mesa lib32-mesa vulkan-radeon lib32-vulkan-radeon

reboot

git clone https://gitlab.com/asus-linux/nvidia-laptop-power-cfg.git
cd nvidia-laptop-power-cfg
# 这里 makepkg 依赖 base-devel 包
makepkg -sfi

sudo systemctl enable nvidia-suspend.service nvidia-hibernate.service nvidia-resume.service
sudo systemctl enable --now nvidia-powerd

reboot
```
安装基础字体, 桌面环境需要
```shell
sudo pacman -S --needed noto-fonts noto-fonts-cjk noto-fonts-emoji
```
安装视频解码
```shell
sudo pacman -S --needed libva-nvidia-driver libvdpau-va-gl libva-utils vdpauinfo vulkan-tools
reboot
```
安装音频依赖
```shell
sudo pacman -S --needed sof-firmware alsa-firmware alsa-ucm-conf alsa-utils pipewire lib32-pipewire wireplumber pipewire-audio pipewire-alsa pipewire-pulse pipewire-jack lib32-pipewire-jack
systemctl --user enable --now pipewire pipewire-pulse wireplumber
reboot
```
安装KDE和一些相关组件
```shell
# NetworkManager 与 KDE 深度集成
# 如果启用 NetworkManager 则应当关闭 systemd-networkd.service, iwd.service (二者存在冲突), 而ModemManager.service 受其支持可选择性开启, systemd-resolved.service 最好保持开启 (若必须关闭则需要配置 /etc/NetworkManager/conf.d/no-systemd-resolved.conf 添加 "[main]\nsystemd-resolved=false", 防止日志一直产生报错) 
# sudo pacman -S --needed networkmanager
# sudo systemctl disable --now systemd-networkd.service
# sudo systemctl disable --now iwd.service
# sudo systemctl enable --now NetworkManager.service
sudo pacman -S --needed plasma-meta konsole dolphin qt6-multimedia-ffmpeg
# 临时启动 KDE 测试是否可用
/usr/lib/plasma-dbus-run-session-if-needed /usr/bin/startplasma-wayland
# 临时启动 SDDM 测试是否可用
sudo systemctl start sddm.service
# 启动开机就进入桌面
sudo systemctl enable sddm.service
```
解决开机后只显示全黑页面和一个光标, 不显示 SDDM 的问题的一种方法
```bash
sudo systemctl edit sddm.service
# 添加以下内容
# [Service]
# ExecStartPre=/bin/sleep 2
sudo systemctl daemon-reload
```

## To-do list

### To be tested

### To be updated

- 独显直连模式 KDE 桌面卡死, 疑似驱动没正确加载
- 添加硬盘分区前清空硬盘格式化操作
- `sudo echo -e xxx >> xxx` 实际不能正常工作, 需要修改
- 配置 KVM
- 配置容器环境 (Docker, etc.)
- 配置 Windows 环境 (wine, steam proton, etc.)
