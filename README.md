# Munbai-01 VM Script Backups

Automated Git backup for scripts, projects, `crontab`, and custom `systemd` unit files from `mumbai-01` (`/home/ubuntu`).

## Structure
- `home_scripts/` — Top-level `.py` and `.sh` scripts from `/home/ubuntu`
- `projects/` — Project directories (`auto_blogpost`, `birthday_bot`, `rahu_bot`, `RiverAlarmApp`)
- `systemd/` — Custom systemd `.service` files from `/etc/systemd/system`
- `crontab.txt` — Export of `crontab -l`
- `backup.sh` — Sync, commit, and push script (scheduled via cron)
