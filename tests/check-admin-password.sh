#!/bin/bash

# Usage: check-admin-password.sh MODULE_ID < password
# Exit 0 if the password read from stdin matches the BBS admin hash.

set -euo pipefail

module_id=$1
password=$(cat)
hash=$(runagent -m "$module_id" podman exec bbs mysql bbs -N -B \
    -e "SELECT password_hash FROM users WHERE username='admin'")
printf '%s\n%s' "$hash" "$password" | runagent -m "$module_id" podman exec -i bbs php -r \
    '[$h, $p] = explode("\n", stream_get_contents(STDIN), 2); exit(password_verify($p, $h) ? 0 : 1);'
