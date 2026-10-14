# ns8-borgbackupserver

[![Publish images](https://github.com/francio87/ns8-borgbackupserver/actions/workflows/publish-images.yml/badge.svg)](https://github.com/francio87/ns8-borgbackupserver/actions/workflows/publish-images.yml)
[![Test module](https://github.com/francio87/ns8-borgbackupserver/actions/workflows/test-module.yml/badge.svg)](https://github.com/francio87/ns8-borgbackupserver/actions/workflows/test-module.yml)
[![Latest release](https://img.shields.io/github/v/release/francio87/ns8-borgbackupserver?sort=semver)](https://github.com/francio87/ns8-borgbackupserver/releases/latest)
[![NethServer 8](https://img.shields.io/badge/NethServer-8-1f6feb)](https://www.nethserver.org/)
[![License: GPL-3.0](https://img.shields.io/github/license/francio87/ns8-borgbackupserver)](LICENSE)

Run [Borg Backup Server](https://github.com/marcpope/borgbackupserver) (BBS) on NethServer 8.

The module runs the upstream BBS image as a single rootless Podman container. BBS includes its own Apache web app, MariaDB, ClickHouse, SSH daemon, and scheduler; the module does not split or modify those services. The upstream image version is pinned in `build-images.sh` and kept up to date by Renovate.

## 📋 Requirements

- At least 2 GB RAM; 4 GB or more is recommended by upstream.
- A DNS name for the BBS web interface.
- TCP 80 and 443 reachable by browsers and agents. With Let's Encrypt, the FQDN must resolve publicly to this node.
- The Borg SSH port reachable by backup clients. NS8 opens it in the node firewall; router/NAT forwarding must be configured separately.

## 🚀 Install

### From the Software Center (recommended)

Add the module repository, then install **Borg Backup Server** from the Software Center:

```bash
api-cli run add-repository --data '{"name":"francio87","url":"https://francio87.github.io/ns8-repomd/","status":true}'
```

The catalog refreshes every six hours. Updates are offered by the Software Center.

### From the image, without adding the repository

Pick a version from the [releases page](https://github.com/francio87/ns8-borgbackupserver/releases) and instantiate it on node `1`:

```bash
add-module ghcr.io/francio87/borgbackupserver:<version> 1
```

The command returns the module ID, for example `borgbackupserver1`. Without the repository, the Software Center does not offer updates: update the instance manually with the image of a newer version:

```bash
api-cli run update-module --data '{"module_url":"ghcr.io/francio87/borgbackupserver:<version>","instances":["borgbackupserver1"]}'
```

The `latest` tag follows the `main` branch and is meant for development only.

## ⚙️ Configure

Configure the module from its Settings page, or run `configure-module` with these parameters:

- `fqdn` (required): host name of the BBS web interface
- `lets_encrypt` (required): request a Let's Encrypt certificate through Traefik
- `ssh_port` (required): external Borg SSH port, from `1024` to `65535` (default `2222`)
- `admin_password` (required on the first configuration only): initial BBS `admin` password; rejected afterwards

Example:

```bash
api-cli run module/borgbackupserver1/configure-module --data - <<EOF
{
  "fqdn": "bbs.example.org",
  "lets_encrypt": true,
  "ssh_port": 2222,
  "admin_password": "<initial password>"
}
EOF
```

Omit `admin_password` in later calls.

Notes:

- The module configuration is authoritative: it sets BBS `APP_URL`, `server_host`, and `SSH_PORT`.
- Before applying a new SSH port, the module checks that it is not already listening on the node or conflicting with the web backend port.
- After changing the SSH port, restart existing agents. After changing the FQDN, also update the server URL saved in each agent configuration.
- Without Let's Encrypt, Traefik uses the node's default certificate. BBS agents verify HTTPS certificates, so they must trust it; a publicly trusted certificate is recommended.
- The first configuration waits for BBS to initialize its database, then sets the `admin` password hash directly in the database through standard input, like a password reset. The password is never written to the module state, the container environment, or the logs, and BBS never generates its own initial password. If the first configuration fails before the password is set, run it again with the password.

## 🔎 Get the configuration

```bash
api-cli run module/borgbackupserver1/get-configuration --data null | jq
```

## 🔑 Recover admin access

From the Settings page, open **Advanced options**, select **Modify password**, and enter the new `admin` password. The optional 2FA checkbox also clears the TOTP secret and recovery codes. Leaving the password fields empty changes only the hostname, certificate, and SSH port.

If the web interface is not reachable, run from a shell on the NS8 node:

```bash
runagent -m borgbackupserver1 bbs-reset-admin-password
```

The command lists the administrator accounts, asks for the account ID and new password, and invalidates pending password-recovery tokens. Add `--reset-2fa` to also clear TOTP setup, so the user can enroll again. Neither method affects MFA managed by an external OIDC provider, and local password login must be enabled for the new password to work.

## 💾 Data, backup and restore

All persistent data lives in the Podman volume `bbs-data`, mounted at `/var/bbs`: client Borg repositories, configuration and `APP_KEY`, SSH host keys, and the ClickHouse catalog.

The NS8 backup includes:

- the `bbs-data` volume, excluding live MariaDB and ClickHouse files and temporary/cache directories;
- a BBS server archive with a MariaDB dump, application configuration, and SSH host keys.

> **After a restore**, open each repository in BBS and run **Rebuild Missing**. The restore imports the database but does not rebuild the ClickHouse catalog, so existing recovery points are not listed until the rebuild completes. This runs as a background task and can take a long time.

Because the volume contains client Borg repositories, NS8 backups can be large and may duplicate data already protected elsewhere. Size the backup destination and retention accordingly.

## ⚠️ Limitations

- Do not use the BBS in-app server updater: it modifies the container outside the pinned image and can apply irreversible database migrations. Update BBS by updating the module.
- SSH ports below `1024` are not supported, because the container is rootless.
- Router/NAT forwarding for the SSH port is not managed by the module.

## 📜 Logs

```bash
runagent -m borgbackupserver1 podman logs bbs
```

## 🗑️ Uninstall

```bash
remove-module --no-preserve borgbackupserver1
```

This deletes the `bbs-data` volume, including all client Borg repositories stored on the server.

## 🧪 Tests

The Robot Framework tests use the NS8 standard testing infrastructure. See the [ns8-github-actions testing guide](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally).

## 📦 Releasing

Versioning, publication, and registry cleanup are described in [RELEASING.md](RELEASING.md).
