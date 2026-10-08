# Borg Backup Server for NethServer 8

This module runs the upstream [Borg Backup Server](https://github.com/marcpope/borgbackupserver) image as a dedicated, rootless Podman container. BBS includes its own Apache web app, MariaDB, ClickHouse, SSH daemon, and scheduler; the module does not split or modify those services.

The upstream image is pinned in `build-images.sh` to `v2.98.5`. Update the BBS server through a newer NS8 module image, not the BBS in-app server updater: that updater changes the container filesystem outside the pinned image and can apply database migrations that are not reversible.

## Requirements

- At least 2 GB RAM; 4 GB or more is recommended by upstream.
- A DNS name for the BBS web interface.
- TCP 80 and 443 reachable by browsers and agents. If using Let's Encrypt, the FQDN must resolve publicly to this node and HTTP validation must succeed.
- The configured Borg SSH TCP port reachable by backup clients. NS8 opens this port in the node firewall; router/NAT forwarding must be configured separately.

## Configure

In the module Settings page, set the FQDN, choose whether NS8 Traefik should request a Let's Encrypt certificate, and select the external SSH port. The default SSH port is `2222`; ports below `1024` are not accepted for this rootless module. Before applying a changed port, the module checks whether it is listening on the node and whether it conflicts with the NS8-assigned web backend port.

The Settings page can optionally set the BBS administrator password during the initial setup. After BBS initializes, the initial-password field is no longer used. Saving the hostname, certificate, or Borg SSH port does not change the BBS password or 2FA. To reset the standard `admin` account password, use **Modify password** in Settings. The optional 2FA checkbox also clears its TOTP secret and recovery codes; MFA managed by an external OIDC provider is not affected. Leaving the initial password empty preserves BBS's generated initial password behavior. The initial password is not returned by module configuration and is cleared from module state after BBS initialization.

If you cannot access the BBS web interface, the emergency command is also available from an interactive shell on the NS8 node:

```bash
runagent -m borgbackupserver1 bbs-reset-admin-password
```

The command lists BBS administrator accounts, prompts for the account ID and new password, and updates the password hash in the BBS database. It also invalidates outstanding password-recovery tokens. By default it leaves two-factor authentication enabled. To reset the BBS TOTP setup at the same time, add `--reset-2fa`:

```bash
runagent -m borgbackupserver1 bbs-reset-admin-password --reset-2fa
```

This option requires confirmation and clears the TOTP secret and recovery codes. The user can then sign in with the new password and enroll 2FA again. It does not reset MFA managed by an external OIDC identity provider. Local password login must be enabled for the new password to work.

For example, if the instance is `borgbackupserver1`:

```bash
api-cli run module/borgbackupserver1/configure-module --data '{"fqdn":"bbs.example.org","lets_encrypt":true,"ssh_port":2222}'
```

The module configuration is authoritative. It sets BBS `APP_URL` and `server_host`, and passes the chosen SSH port both to the container's host-port mapping and BBS `SSH_PORT` setting. BBS receives the same SSH port advertised to agents. Restart existing agents after changing the port. A hostname change also requires updating the saved server URL in existing agent configurations; the server cannot rewrite those local client files.

With Let's Encrypt disabled, Traefik uses the node's default certificate. BBS agents verify HTTPS certificates, so unattended agents must trust that certificate; a publicly trusted certificate is recommended when clients cannot be configured with the node's certificate.

If you leave the initial password field empty, BBS generates an administrator password on first startup and prints it to the container log. To read the log, run `runagent -m borgbackupserver1 podman logs bbs`.

## Data and backup

All BBS persistent files live in the named Podman volume `bbs-data`, mounted at `/var/bbs`. This includes Borg repositories, configuration and `APP_KEY`, SSH host keys, and ClickHouse catalog data. The module's NS8 backup includes that volume and generates an additional BBS server archive containing a MariaDB dump, application configuration, and SSH host keys. The live MariaDB and ClickHouse files plus temporary/cache directories are excluded from Restic; ClickHouse catalogs are intentionally rebuilt from Borg repositories, and restore imports the SQL dump before applying the module configuration.

Because the volume includes client Borg repositories, NS8 backups can be large and may duplicate data already protected elsewhere. Ensure the configured NS8 backup destination has enough capacity and retention appropriate for those repositories.

## Install

Build and publish the module image, then instantiate it on an NS8 node:

```bash
add-module ghcr.io/francio87/borgbackupserver:0.0.1 1
```

The command returns the module ID. Configure it in the NS8 UI or with `configure-module` as shown above.

## Tests

The Robot Framework tests use the NS8 standard testing infrastructure. See the [ns8-github-actions testing guide](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally).
