---
id: dns-resolution
title: DNS and Name Resolution Issues
owner: IT Service Desk
last_reviewed: 2026-10-01
---
# DNS and Name Resolution Issues

This guide covers cases where a computer cannot find internal or external systems by name.
All names and addresses are fictional.

## Symptoms

- Internal sites such as `intranet.acme.example` show "server not found",
  "DNS_PROBE_FINISHED_NXDOMAIN" or "This site can't be reached", while public websites work.
- Public websites do not open, but pinging an IP address works.
- One user is affected while colleagues on the same network are not.

## Information to collect

- The exact name the user typed and the full error message.
- Whether the user is in the office, at home on the VPN, or at home without the VPN.
- The output of `ipconfig /all` (Windows) or the network details (macOS).

## Quick checks

1. Internal names only work in the office or when the VPN is connected. Confirm the VPN is
   connected if the user is remote.
2. Check that the address was typed correctly, including the `.acme.example` suffix.
3. Ask whether other users at the same location have the same problem.

## Troubleshooting steps

1. Clear the DNS cache. Windows: run `ipconfig /flushdns` in a command prompt. macOS: run
   `sudo dscacheutil -flushcache` in Terminal.
2. Test name resolution with `nslookup intranet.acme.example`. In the office the answer must
   come from the DNS servers `10.20.0.10` or `10.20.0.11`.
3. If `nslookup` uses a different DNS server (for example a home router), disconnect and
   reconnect the VPN so that the company DNS settings are applied.
4. Check the hosts file for manual entries for the failing name. Windows:
   `C:\Windows\System32\drivers\etc\hosts`. Remove entries only with the user's agreement and
   note them in the ticket.
5. Restart the computer and test again.

## Escalation criteria

Escalate to **Network Team (Tier 2)** when:

- Several users or a whole office cannot resolve internal names (possible DNS server outage).
- `nslookup` shows the correct company DNS servers but returns no answer or a wrong address.
- A name resolves to an unexpected external address. Treat this as a possible security issue
  and also inform the **Security Team**.
