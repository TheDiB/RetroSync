# Batocera SSH setup (manual, read-only activity detection)

This documents the **observed Batocera 44 / Steam Deck** setup. The v0.9 `--setup` wizard **exists**, but only records an optional existing SSH endpoint in a new config file. It does **not** verify host identity, enroll keys, install authorized keys or change SSH settings. SSH access alone does not authorize save writes.

## 1. Verify Batocera identity before trusting it

Batocera 44 in our tests uses Dropbear. Its **server host keys** are in `/userdata/system/ssh/`, for example `dropbear_ed25519_host_key`. On Batocera, display its public key:

```sh
dropbearkey -y -f /userdata/system/ssh/dropbear_ed25519_host_key
```

On Steam Deck, retrieve the advertised host key and compare fingerprints **out of band**:

```sh
ssh-keyscan -T 5 -t ed25519 BATOCERA_IP > /tmp/batocera-hostkey.pub
ssh-keygen -lf /tmp/batocera-hostkey.pub
```

Do not trust a key just because `ssh-keyscan` returned it. Only after fingerprints match, add the verified host key to `~/.ssh/known_hosts`, preserving existing entries and permissions.

## 2. Generate a dedicated client key

On Steam Deck, verify that the target key path is unused:

```sh
ls -la ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_retrosync -C "RetroSync Steam Deck"
```

Do not overwrite existing keys. Keep the **private** key on the Steam Deck. A passphrase-protected key requires an unlocked SSH agent for noninteractive checks; a passphrase-free key requires careful local access control.

## 3. Authorize the client key on Batocera

On the tested Batocera 44, `root` has home directory `/userdata/system` (verify with `grep '^root:' /etc/passwd`). Dropbear consults:

```text
/userdata/system/.ssh/authorized_keys
```

**Mind the dot:** `/userdata/system/ssh/` (without dot) contains Dropbear **server host keys**; `/userdata/system/.ssh/` (with dot) contains **client authorization**.

Using an already authorized Batocera shell session, create `/userdata/system/.ssh/` if needed, **append rather than replace** the Steam Deck public key in `authorized_keys`, and set directory permissions to `700` and file permissions to `600`. Never copy the private key to Batocera. Initial authorized access is required; RetroSync cannot bypass SSH authentication.

## 4. Configure and test the Steam Deck SSH client

Add an entry to `~/.ssh/config` without overwriting existing settings:

```sshconfig
Host BATOCERA_IP
    HostName BATOCERA_IP
    User root
    IdentityFile ~/.ssh/id_ed25519_retrosync
    IdentitiesOnly yes
    StrictHostKeyChecking yes
```

Replace `BATOCERA_IP` with the actual address and run `chmod 600 ~/.ssh/config`.

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes root@BATOCERA_IP 'ps -eo pid=,comm='
```

Then add the optional `batocera` object in private `config.json` (or supply it during `--setup`) and run:

```sh
python3 retro_sync.py --config config.json --check
```

The remote check is a snapshot of **RetroArch only**. `STOPPED` does not guarantee the NAS is idle; `UNKNOWN` must never be treated as permission to write.
