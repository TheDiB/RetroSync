# Batocera SSH setup (manual, read-only activity detection)

This documents the **observed Batocera 44 / Steam Deck** setup. The planned `--setup` wizard does **not** exist yet. SSH access alone does not permit safe synchronization writes.

## 1. Verify Batocera identity before trusting it

Batocera 44 in our test runs Dropbear. Its **server host keys** are in `/userdata/system/ssh/`, for example `dropbear_ed25519_host_key`. On Batocera, display its fingerprint:

```sh
dropbearkey -y -f /userdata/system/ssh/dropbear_ed25519_host_key
```

On Steam Deck, retrieve the advertised public host key and compare fingerprints **out of band**:

```sh
ssh-keyscan -T 5 -t ed25519 BATOCERA_IP > /tmp/batocera-hostkey.pub
ssh-keygen -lf /tmp/batocera-hostkey.pub
```

Do not trust a key just because `ssh-keyscan` returned it. Only after the fingerprints match, append the verified host key to `~/.ssh/known_hosts` (preserving existing entries) and set appropriate file permissions.

## 2. Generate a dedicated client key

On Steam Deck, first check that the target key path is unused:

```sh
ls -la ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_retrosync -C "RetroSync Steam Deck"
```

Do not overwrite existing keys. Keep the **private** key on the Steam Deck. A passphrase-protected key needs an unlocked SSH agent for noninteractive checks; a passphrase-free key requires especially careful local access control.

## 3. Authorize the client key on Batocera

On the tested Batocera 44, `root` has home directory `/userdata/system` (verify with `grep '^root:' /etc/passwd`). Dropbear consults:

```text
/userdata/system/.ssh/authorized_keys
```

**Mind the dot:** `/userdata/system/ssh/` (without dot) contains Dropbear **server host keys**; `/userdata/system/.ssh/` (with dot) contains **client authorization**.

With an already authorized Batocera shell session, create `/userdata/system/.ssh/` if necessary, append (do not replace) the Steam Deck's `id_ed25519_retrosync.pub` as one complete line in `authorized_keys`, and set directory permissions to `700` and file permissions to `600`. Never copy the private key to Batocera. Initial authorized access is required; RetroSync cannot bypass SSH authentication.

## 4. Configure and test the Steam Deck SSH client

Add an entry to `~/.ssh/config` without overwriting existing configuration:

```sshconfig
Host BATOCERA_IP
    HostName BATOCERA_IP
    User root
    IdentityFile ~/.ssh/id_ed25519_retrosync
    IdentitiesOnly yes
    StrictHostKeyChecking yes
```

Replace `BATOCERA_IP` with the actual host address and run `chmod 600 ~/.ssh/config`.

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@BATOCERA_IP 'ps -eo pid=,comm='
```

Then add the optional `batocera` object in private RetroSync `config.json` and run:

```sh
python3 retro_sync.py --config config.json --check
```

The remote check is a snapshot of **RetroArch only**. `STOPPED` does not guarantee the NAS is idle; `UNKNOWN` must never be treated as permission to write.
