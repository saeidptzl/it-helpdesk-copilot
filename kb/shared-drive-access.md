---
id: shared-drive-access
title: Shared Drive Access (S: drive)
owner: IT Service Desk
last_reviewed: 2026-10-01
---
# Shared Drive Access (S: drive)

This guide covers access to the department shared drive, mapped as `S:` to
`\\files.acme.example\shared`. All names and paths are fictional.

## Symptoms

- The S: drive is missing from This PC or shows a red cross, for example after a Windows update
  or a password change.
- Opening a folder shows "Access denied" or "You don't have permission".
- Files open as read-only although the user needs to edit them.

## Information to collect

- The full path of the folder or file, for example `S:\Finance\Reports`.
- The exact error message.
- Whether the user changed department or role recently.
- Whether colleagues in the same team can open the same folder.

## Quick checks

1. If the user is remote, confirm the VPN is connected. The shared drive is not reachable from
   the internet.
2. Open `\\files.acme.example\shared` directly in File Explorer to check whether the server is
   reachable.
3. Ask the user to sign out of Windows and sign in again. Group membership changes only apply
   after a new sign-in.

## Reconnecting the S: drive

1. Open File Explorer > This PC > Map network drive.
2. Choose the letter `S:` and the folder `\\files.acme.example\shared`.
3. Tick "Reconnect at sign-in" and confirm.
4. If Windows asks for credentials, the user signs in with their normal company account.

## Access and permission requests

- Folder permissions are granted by the **folder owner** listed in the IT portal, not by the
  service desk.
- If the user needs access to a new department folder (for example after a role change), ask
  them to submit an access request in the IT portal at `help.acme.example`. The request is
  approved by their manager and the folder owner.
- The service desk must not add users to security groups directly.

## Escalation criteria

Escalate to **Infrastructure Team (Tier 2)** when:

- The file server does not respond for several users.
- Files or folders appear to be missing for a whole team (also follow the backup and restore
  guide).
- Many files suddenly have unknown extensions or a ransom note appears. Treat this as a
  security incident: tell the user to disconnect from the network and contact the
  **Security Team** immediately.
