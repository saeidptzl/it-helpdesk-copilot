---
id: printer-connectivity
title: Printer Connectivity
owner: IT Service Desk
last_reviewed: 2026-10-01
---
# Printer Connectivity

This guide covers office network printers such as `PRN-OPS-01` (ground floor) and
`PRN-OPS-02` (second floor). All names and addresses are fictional.

## Symptoms

- The printer shows "Offline" on the user's computer.
- Print jobs stay in the queue and never print.
- Pages print with random characters or wrong formatting.
- The printer is missing from the list of available printers.

## Information to collect

- The printer name from the label on the device, for example `PRN-OPS-02`.
- Whether other users can print to the same printer.
- Any message shown on the printer's own display.

## Quick checks

1. Check the printer's display for errors such as paper jam, empty tray or low toner.
2. Confirm the user's computer is on the office network (cable or the `ACME-OFFICE` Wi-Fi).
   Printers cannot be reached from the guest Wi-Fi or from home.
3. Ask a colleague to print a test page. If nobody can print, the problem is the printer or
   the print server, not the user's computer.

## Troubleshooting steps

1. Clear stuck jobs: open Settings > Bluetooth & devices > Printers & scanners, select the
   printer, open the print queue and cancel all documents.
2. Restart the Print Spooler service (Services > Print Spooler > Restart), or restart the
   computer.
3. Remove the printer and add it again from the print server `print.acme.example`, which also
   installs the correct driver.
4. If pages print with random characters, remove the printer and add it again from the print
   server. Garbled output usually means a wrong or outdated driver.

## Escalation criteria

Escalate to **Facilities and Print Support** when:

- The printer shows a hardware error code on its display, or nobody can print to it.
- There is a paper jam that cannot be cleared by following the instructions on the device.
- A new printer must be installed or moved to another location.
