---
id: backup-restore
title: Backup and File Restore Requests
owner: IT Service Desk
last_reviewed: 2026-10-01
---
# Backup and File Restore Requests

This guide covers requests to recover deleted or overwritten files. All names, paths and
retention values are fictional.

## What is backed up

- The shared drive `\\files.acme.example\shared` (S:) is backed up every night at 01:00.
  Backups are kept for 30 days.
- Laptop files are protected only if they are saved in the user's synced cloud folder.
  Files saved only on the desktop or in local folders are not backed up.
- Email is not covered by this guide.

## Typical requests

- A file or folder was deleted by mistake.
- A file was overwritten or damaged, by a person or by a script or program, and the user needs an
  earlier version.
- The user needs the content of a folder as it was on a specific date.

## Self-service restore of previous versions

Users can often recover a file themselves:

1. In File Explorer, right-click the file or folder on the S: drive and choose
   Properties > Previous Versions.
2. Select a version from before the problem happened and choose Open to check it.
3. Use Restore to overwrite the current file, or Copy to save the old version elsewhere.

## Information to collect for a restore request

- The full path of the file or folder, for example `S:\Finance\Q3-forecast.xlsx`.
- The date and approximate time when the file was last correct.
- Whether the file was deleted, overwritten or damaged.
- Whether the old version should replace the current file or be restored next to it.

## Restore request steps

1. Try the self-service restore above with the user first.
2. If that does not work, create a restore request in the IT portal at `help.acme.example`
   with the information collected above.
3. Tell the user that standard restores are completed within one business day.

## Escalation criteria

Escalate to **Infrastructure Team (Tier 2)** when:

- The file was deleted or changed more than 30 days ago (outside normal retention).
- A whole folder or more than 1,000 files must be restored.
- Many files were changed at once by an unknown program, or files have unknown extensions.
  Treat this as a possible ransomware incident and contact the **Security Team** immediately.
