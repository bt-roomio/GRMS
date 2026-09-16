{% autoescape off %}#!/bin/bash
#
# Roomio fleet agent bootstrap for {{ code }}
# Generated {{ generated_at }} — the setup key below is single-use and expires shortly.
#
# DO NOT paste this line by line. It must run as root, start to finish, in one
# process: half of it needs root, and `sudo cmd > file` fails regardless of sudo
# because the redirect is done by your own unprivileged shell.
#
#   curl -fsSL '<install link>' | sudo bash
#
# Re-running it is safe, and is how you re-enrol a node.
#
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Not root. Run the whole script at once: curl -fsSL <install link> | sudo bash" >&2
  exit 1
fi

# Keep apt and needrestart from opening a dialog: there is no terminal to answer
# it on when this arrives through a pipe, and it would hang forever.
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

echo "==> Installing NetBird"
if ! command -v netbird >/dev/null 2>&1; then
  curl -fsSL https://pkgs.netbird.io/install.sh | sh
fi

# 'netbird up' silently ignores its flags when a session is already live.
netbird down >/dev/null 2>&1 || true

echo "==> Joining the mesh as {{ code }}"
# One line deliberately: a continuation followed by a blank line breaks this.
# --allow-server-ssh=false is required — NetBird's own SSH server hijacks port 22
# and reroutes it to 22022, swallowing our SSH and Ansible traffic.
netbird up --setup-key {{ setup_key }} --management-url {{ management_url }} --allow-server-ssh=false --hostname {{ code }}

echo "==> Creating the {{ ssh_user }} account"
id -u {{ ssh_user }} >/dev/null 2>&1 || useradd -m -d {{ ssh_home }} -s /bin/bash {{ ssh_user }}
# `useradd -m` only owns a home it creates itself, and the check above skips
# useradd entirely when the account already exists. Either way a pre-existing
# {{ ssh_home }} stays root-owned, and file uploads land there.
install -d -o {{ ssh_user }} -g {{ ssh_user }} {{ ssh_home }}
chown {{ ssh_user }}:{{ ssh_user }} {{ ssh_home }}

echo "==> Installing the backend public key"
install -d -m 700 -o {{ ssh_user }} -g {{ ssh_user }} {{ ssh_home }}/.ssh
cat > {{ ssh_home }}/.ssh/authorized_keys <<'ROOMIO_KEY_EOF'
{{ public_key }}
ROOMIO_KEY_EOF
chmod 600 {{ ssh_home }}/.ssh/authorized_keys
chown {{ ssh_user }}:{{ ssh_user }} {{ ssh_home }}/.ssh/authorized_keys

echo "==> Granting sudo"
# Full sudo for now; narrowing it to root-owned wrapper scripts is planned.
# Validated in a temp file first — a malformed /etc/sudoers.d entry locks sudo
# out for everyone on the box.
echo '{{ ssh_user }} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/.{{ ssh_user }}.tmp
chmod 440 /etc/sudoers.d/.{{ ssh_user }}.tmp
visudo -cf /etc/sudoers.d/.{{ ssh_user }}.tmp >/dev/null
mv /etc/sudoers.d/.{{ ssh_user }}.tmp /etc/sudoers.d/{{ ssh_user }}

echo "==> Making sure sshd is running"
systemctl enable --now ssh >/dev/null 2>&1 || systemctl enable --now sshd >/dev/null 2>&1 || true

echo
echo "Done. Mesh status:"
netbird status || true
echo
echo "{{ code }} will appear online in Roomio within about a minute."
{% endautoescape %}
