#!/bin/bash
# Isaac 环境一键复原脚本 v2 — 2026-10-22 D2 判定项通过后固化
# 适用 Ubuntu 22.04 + NVIDIA 驱动>=525。含全部 10 个坑的标准修法。
# 前置：本脚本所在机器需能访问外网；GitHub 不可达时按 [备注] 从本地上传。
set -e

echo "=== [1/7] 系统依赖（libGLU/libXt 首启坑）==="
sudo apt update && sudo apt install -y git tmux htop build-essential wget \
  libgl1 libxrender1 libxext6 libglu1-mesa libxi6 libsm6 libxkbcommon-x11-0 libxt6

echo "=== [2/7] conda 环境（清华镜像防 Errno11）==="
[ -d ~/miniconda3 ] || { wget -q https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/mc.sh && bash /tmp/mc.sh -b -p ~/miniconda3; }
~/miniconda3/bin/conda create -n isaaclab python=3.10 -y --override-channels \
  -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ || true
source ~/miniconda3/etc/profile.d/conda.sh && conda activate isaaclab
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

echo "=== [3/7] flatdict 坑（setuptools<81 + 无构建隔离）==="
pip install "setuptools<81" wheel
pip install flatdict==4.0.1 --no-build-isolation

echo "=== [4/7] pip 侧 Isaac（[sim] extra 不存在；isaacsim 必须 [all]）==="
pip install isaaclab==2.1.0
pip install "isaacsim[all]"

echo "=== [5/7] IsaacLab v2.1.0 源码（关键：pip isaaclab 是空壳，envs 必须源码安装）==="
# [备注] 云端 GitHub 不通时：本地下载 https://github.com/isaac-sim/IsaacLab/archive/refs/tags/v2.1.0.tar.gz
#        解包后打包 source/ 五个子目录 + apps/ 上传（scp）到 ~/ 再解压到 ~/IsaacLab-2.1.0/
if [ ! -d ~/IsaacLab-2.1.0/source/isaaclab ]; then
  wget -q https://github.com/isaac-sim/IsaacLab/archive/refs/tags/v2.1.0.tar.gz -O /tmp/il.tar.gz || echo "[警告] GitHub 不通，请按[备注]从本地上传"
  tar -xzf /tmp/il.tar.gz -C ~ IsaacLab-2.1.0/source IsaacLab-2.1.0/apps 2>/dev/null || tar -xzf /tmp/il.tar.gz -C ~
fi
for pkg in isaaclab isaaclab_assets isaaclab_tasks isaaclab_rl isaaclab_mimic; do
  pip install -e ~/IsaacLab-2.1.0/source/$pkg --no-deps -q
done

echo "=== [6/7] AMP 仓库（GitHub 不通时本地打包 third_party 上传）==="
[ -d ~/Mini-Pi-Plus_AMP ] || git clone --depth 1 https://github.com/HighTorque-Robotics/Mini-Pi-Plus_AMP.git ~/
cd ~/Mini-Pi-Plus_AMP
pip install -e . -q && pip install -e rsl_rl -q

echo "=== [7/7] 仓库补丁（版本适配三件套）==="
# a) COM 随机化垫片（isaaclab 2.1.0 无此函数，回放用 no-op）
grep -q randomize_rigid_body_com legged_lab/mdp/__init__.py || cat >> legged_lab/mdp/__init__.py << 'EOF'

def randomize_rigid_body_com(env, env_ids=None, asset_cfg=None, com_range=None, **kwargs):
    """No-op placeholder for center-of-mass randomization term."""
    pass
EOF
# b) 四元数 API 改名（quat_apply_inverse -> quat_rotate_inverse）
grep -rl 'quat_apply_inverse' legged_lab --include='*.py' | xargs -r sed -i 's/quat_apply_inverse/quat_rotate_inverse/g'
# c) checkpoint 摆位
mkdir -p logs/pi_plus_amp_sym_flat/exported && cp -n Exported_policy/*.pt logs/pi_plus_amp_sym_flat/exported/ || true

echo "=== 复原完成。验证：python legged_lab/scripts/play_log.py --task=pi_plus_amp_sym_flat --load_run=exported --checkpoint=model_40000.pt --num_envs=1 --headless ==="
