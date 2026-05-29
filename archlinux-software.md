# archlinux 用到的软件包列表

## 通过 `sudo pacman -S packages` 安装

温度监控: `btop`

输入法: `fcitx5-im fcitx5-chineae-addons fcitx5-pinyin-zhwiki`

浏览器: `firefox`

容器: `docker nvidia-container-toolkit`

## 配置 tensorflow 环境

为了使系统干净整洁, 建议通过 docker 配置环境

首先安装 docker 和 nvidia-container-toolkit, 使用 docker 时通过手动启用 docker 服务 `sudo systemctl start docker.socket` (对于个人用户启用 docker.socket 而不是 docker.server 更快, 并且为了减少系统待机占用选择不自启动 docker 服务)

由于 tensorflow 的官方镜像无法调用 gpu, 选择镜像 `nvidia/cuda:12.5.1-cudnn-devel-ubuntu22.04`, 注意这里的 cuda tooklit 版本选择, 宿主机通过 nvidia-smi 查看的 cuda 版本不一定是tensorflow所使用的, 需要通过执行 python 脚本 `python3 -c "import tensorflow as tf; print(tf.sysconfig.get_build_info())"` 来查看 tensorflow 使用的 cuda toolkit 版本, 或者在官网查看 [https://www.tensorflow.org/install/source](https://www.tensorflow.org/install/source)

然后创建容器, 在容器内部安装 python, 并通过 pip 安装 tensorflow `pip3 install tensorflow[and-cuda]`, 这里遵循官方教程即可, 由于容器已经安装好 cuda 和 cudnn, 无需再次安装

最后通过 `python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"` 检查 gpu 是否可用
