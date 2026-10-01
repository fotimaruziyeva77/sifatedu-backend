#!/usr/bin/env bash
# Yangi Ubuntu 24.04 serverni Sifat Edu uchun tayyorlaydi. Bir marta, root sifatida:
#   bash /srv/sifatedu/infra/deploy/setup-server.sh
# Qayta ishga tushirilsa zarar qilmaydi: borini qayta o'rnatmaydi. Qo'llanma: docs/DEPLOY.md
set -Eeuo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "root sifatida ishga tushiring: sudo bash $0" >&2
    exit 1
fi

step() { printf '\n==> %s\n' "$*"; }
export DEBIAN_FRONTEND=noninteractive

step "Vaqt zonasi: Asia/Tashkent"
timedatectl set-timezone Asia/Tashkent

step "Tizim yangilanishlari va kerakli dasturlar"
apt-get update -q
apt-get -y -q upgrade
apt-get -y -q install ca-certificates curl git ufw fail2ban unattended-upgrades certbot openssl

step "Swap 4 GB: xotira yetmay qolsa jarayonlar o'chib qolmasin"
if [ -z "$(swapon --show)" ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile > /dev/null
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
cat > /etc/sysctl.d/90-sifatedu.conf <<'EOF'
# Swap faqat zarur bo'lganda; Redis fon saqlashi (fork) uchun overcommit.
vm.swappiness = 10
vm.overcommit_memory = 1
EOF
sysctl --system > /dev/null

step "Docker"
if ! command -v docker > /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    # shellcheck source=/dev/null
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc]" \
        "https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
        docker-compose-plugin
fi
# Konteyner loglari diskni to'ldirmasin; Docker Hub sekin yoki yopiq bo'lsa — Google mirror.
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" },
  "registry-mirrors": ["https://mirror.gcr.io"]
}
EOF
systemctl enable docker > /dev/null
systemctl restart docker

step "Firewall: faqat SSH, HTTP va HTTPS"
ufw allow OpenSSH > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw --force enable > /dev/null
ufw status | head -n 8

step "fail2ban (parolni taxmin qilishdan himoya) va avtomatik xavfsizlik yangilanishlari"
systemctl enable --now fail2ban > /dev/null
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

step "SSH: faqat kalit bilan kirish"
if [ -s /root/.ssh/authorized_keys ]; then
    # Birinchi o'qilgan qiymat amal qiladi: 01- fayl bulut sozlamalaridan (50-cloud-init) oldin.
    cat > /etc/ssh/sshd_config.d/01-sifatedu.conf <<'EOF'
# Sifat Edu: parol bilan kirish o'chirilgan, faqat SSH kalit.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
    mkdir -p /run/sshd
    sshd -t
    systemctl reload ssh 2> /dev/null || true
    echo "Parol bilan kirish o'chirildi, kalit bilan kirish ishlaydi."
else
    echo "OGOHLANTIRISH: /root/.ssh/authorized_keys bo'sh — parol bilan kirish hozircha qoldirildi."
    echo "SSH kalitni qo'shing (docs/DEPLOY.md, 3-qadam) va skriptni qayta ishga tushiring."
fi

step "Tayyor"
docker --version
docker compose version
free -h | sed -n '1,3p'
df -h / | tail -n 1
