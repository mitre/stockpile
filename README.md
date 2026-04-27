# MITRE Caldera plugin: Stockpile

## Overview:

The Stockpile plugin supplies Caldera with TTPs and adversary profiles. This plugin serves as the core repository of abilities, adversaries, planners and facts.
These components are all loaded through the `plugins/stockpile/data/*` directory.

### Context:
Repository for abilities, adversaries, and facts

### Known Limitations:

- The `donut-shellcode` python package is not currently supported for ARM chip architectures. Thus the package cannot be installed on newer Mac systems with the M chip series.

## Installation:

This is a core CALDERA plugin and is loaded by default via the plugin loader. Ensure it is present in the `plugins/` directory and listed as enabled in your active configuration file (e.g., `conf/default.yml`).

## Dependencies/Requirements:

No additional dependencies are required beyond a standard CALDERA installation.

## Getting Started:

For collection and exfiltration abilities added January 2022 (see list below), additional information
for configuring these abilities can be found in the [examples](docs/Exfiltration-How-Tos.md) in the stockpile/docs/ 
folder.

*2022 Included abilities:*
- Advanced File Search and Stager
- Find Git Repositories & Compress Git Repository
- Compress Staged Directory (Password Protected)
- Compress Staged Directory (Password Protected) and Break Into Smaller Files
- Exfil Compressed Archive to FTP
- Exfil Compressed Archive to Dropbox
- Exfil Compressed Archive to GitHub Repositories | Gists
- Exfil Compressed Archive to GitHub Gist
- Exfil Directory Files to Github (this exfiltrates files without archiving)
- Exfil Compressed Archive to S3 via AWS CLI
- Transfer Compressed Archive to Separate S3 Bucket via AWS CLI
- Scheduled Exfiltration