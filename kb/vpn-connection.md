---
id: vpn-connection
title: VPN Connection Problems
owner: IT Service Desk
last_reviewed: 2026-10-01
---
# VPN Connection Problems

This guide covers problems with the Acme SecureConnect VPN client used to reach internal
systems from home, hotels or customer sites. All names and addresses are fictional.

## Symptoms

- The VPN client shows "Authentication failed" or keeps asking for the password.
- The client shows "Gateway unreachable" or stays on "Connecting...".
- The VPN connects but drops after a few minutes, often on public or hotel Wi-Fi.
- The VPN is connected but internal sites or the S: drive do not open.

## Information to collect

- The exact error message and the time it happened.
- The network the user is on (home, hotel, mobile hotspot, customer site).
- Whether the user changed their password recently.
- The SecureConnect client version (Help > About).

## Quick checks

1. Confirm the device has working internet access by opening a public website.
2. Confirm the user is connecting to the gateway `vpn.acme.example`.
3. If the password was changed recently, ask the user to sign out of the client, restart it
   and sign in with the new password. Cached credentials are the most common cause of
   "Authentication failed".
4. Make sure the multi-factor authentication (MFA) prompt was approved on the user's phone
   within 60 seconds.
5. Check the system clock. A clock that is more than five minutes off breaks authentication.

## Troubleshooting steps

1. Restart the SecureConnect client completely (right-click the tray icon > Exit), then start
   it again.
2. If the connection drops on hotel or public Wi-Fi, ask the user to try a mobile hotspot.
   Some public networks block VPN traffic or disconnect idle sessions.
3. If the VPN connects but internal sites do not open, follow the DNS guide: the problem is
   usually name resolution, not the tunnel.
4. Reinstall the client from the Software Center if the version is older than 6.2 or if the
   client crashes on start.
5. Ask the user to reboot the device after reinstalling and test again.

## Escalation criteria

Escalate to **Network Team (Tier 2)** when:

- More than three users report VPN failures at the same time (possible gateway outage).
- "Authentication failed" continues after the cached-credential and MFA checks above.
- The account appears locked or disabled. The service desk does not unlock accounts from this
  guide; identity changes follow the access-management process.
- The client is up to date, the network works, and the tunnel still drops repeatedly.

Include the information collected above in the escalation.
