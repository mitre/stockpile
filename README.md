# CALDERA plugin: Stockpile

A plugin supplying CALDERA with TTPs and adversary profiles.

[Read the full docs](https://github.com/mitre/caldera/wiki/Plugin:-stockpile)

## Outline
- Adversary Selection (exact vs. behavior)
    - Approach: https://attackevals.mitre.org/methodology/
    - Emulation Plans available online 
- Abilities Definition
- Create clipboard ability 
    - Copy Clipboard: https://attack.mitre.org/techniques/T1115/
- Facts (briefly)
- Adversary Definition
- [Break-out] Create screen capture ability
    - Screen Capture: https://attack.mitre.org/techniques/T1113/
    
Create an Ability (Copy User Clipboard):
- Darwin: `pbpaste`
- Linux: `xclip -o`
- Windows: `Get-Clipboard -raw`

Create an adversary (Ability + Discovery Pack):
0f4c3c67-845e-49a0-927e-90ed33c044e0

Create an Ability (Screen Capture):
	Darwin: `screen capture -t png screen.png`
	Windows: see below

#### Copy Clipboard
```
---

- id: dd999ebe-7d4e-42b7-946c-2513b6788e8a
  name: Copy Clipboard
  description: copy the contents for the clipboard and print them
  tactic: collection
  technique:
    attack_id: T1115
    name: Clipboard Data
  platforms:
    darwin:
      sh:
        command: |
          pbpaste
        parsers:
          plugins.stockpile.app.parsers.basic:
            - source: demo.clipboard.raw
    windows:
      psh,pwsh:
        command: |
          Get-Clipboard -raw
        parsers:
          plugins.stockpile.app.parsers.basic:
            - source: demo.clipboard.raw
    linux:
      sh:
        command: |
          xclip -o
        parsers:
          plugins.stockpile.app.parsers.basic:
            - source: demo.clipboard.raw
```

#### ATT&CKCon Adversary
```
---

id: 0b007fc9-e5d3-495e-a128-56089899339b
name: ATT&CKCon
description: ATT&CKCon
visible: 1
packs:
  - 0f4c3c67-845e-49a0-927e-90ed33c044e0  # discovery pack
phases:
  1:
    - dd999ebe-7d4e-42b7-946c-2513b6788e8a  # copy clipboard
  # add more abilities here
```

#### Windows Screen Capture
```
[Reflection.Assembly]::LoadWithPartialName("System.Drawing")
function screenshot([Drawing.Rectangle]$bounds, $path) {
   $bmp = New-Object Drawing.Bitmap $bounds.width, $bounds.height
   $graphics = [Drawing.Graphics]::FromImage($bmp)

   $graphics.CopyFromScreen($bounds.Location, [Drawing.Point]::Empty, $bounds.size)

   $bmp.Save($path)

   $graphics.Dispose()
   $bmp.Dispose()
}

$bounds = [Drawing.Rectangle]::FromLTRB(0, 0, 1000, 900)
screenshot $bounds "C:\screenshot.png"
```