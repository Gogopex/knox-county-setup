# Knox County Vanilla++

A curated Project Zomboid setup aiming for more realistic survival. Steam downloads the mods; this installs our compatibility changes and optional adjustments.

This first release is for **Windows x64, Project Zomboid 42.21.0 (Steam build 25485521), single player**. It refuses other game builds rather than installing incompatible engine classes.

## Install

1. Subscribe to [Main](https://steamcommunity.com/sharedfiles/filedetails/?id=3836683250) and, if wanted, [Optional Extras](https://steamcommunity.com/sharedfiles/filedetails/?id=3836684696). Finish the Steam downloads.
2. Download the Windows ZIP from [Releases](https://github.com/Gogopex/knox-county-setup/releases/latest), extract it and run `KnoxCountySetup.exe`.
3. Choose whether to include the extra vehicles, music and Lifestyle; Xen; and our gameplay adjustments. Click **Install / Update** with the game closed.
4. If ZombieBuddy needs installation, our manager downloads its official, checksum-verified [GitHub Windows installer](https://github.com/zed-0xff/ZombieBuddy/releases/tag/windows_installer). Follow that installer’s prompts for normal launch. It uses the subscribed Workshop files for the runtime. Then our installation continues.
5. Use **Play** in the setup manager, with Steam running. Start a new Sandbox world and choose **Knox County** under saved sandbox presets if using our adjustments.

The profile is `%USERPROFILE%\Zomboid\KnoxCounty` by default. Its saves and enabled mod selection are separate from your usual Zomboid profile. Keep the extracted setup manager somewhere convenient to use Play again. Steam’s ordinary Play button without the profile argument opens your usual profile.

Better Car Physics installs three engine overrides in the game folder. Those files, and ZombieBuddy, affect other profiles using that game installation too. Our changes are backed up. ZombieBuddy’s installer manages its own installation and uninstall separately.

Some Main integrations also use the small DAMN library, which appears in Extras. If you skip Extras, the manager links any missing individual downloads; you do not need the whole fleet.

## Updates and restore

Steam updates the downloaded upstream mods. **Install / Update** builds new playable copies and reapplies our applicable fixes. It keeps the existing setup if an expected patch input changed. That means an upstream update sometimes needs a revised integration release before it can be installed.

**New releases** checks GitHub and opens the latest download if available. Extract that release and run its executable against the same profile directory. This first version does not replace its own running executable automatically.

**Check** compares the managed mod and engine files with the installed record. Personal settings are seeded only when missing; subsequent updates retain your choices. Installing again applies the choices in the manager to new-world defaults, not to an existing save’s enabled mods or saved sandbox values. Choose your content before creating a world.

**Restore** returns the previous managed mod files and engine overrides. It refuses files edited since installation, and leaves saves untouched. It does not rewind a world you have played with newer mods. ZombieBuddy can be uninstalled using its own upstream installer.

Receipts and backups live under the profile’s `.setup/backups` directory. Keep them if you want rollback. An interrupted installation must be restored before trying again.

## What is included

- Integration for Marz / Vanilla Weapons Plus / Ammo Maker, vehicle effects / Summer Car / Snow, solar / LG electricity, and camper / RV interiors.
- Our inventory, context-menu, hotbar, crafting and bag-action fixes.
- Optional loot, archery, pushing and Lifestyle cleanup adjustments.
- A new-world sandbox preset and selected mod preferences.

The package contains patch recipes, our additions and copies/renames to perform locally. It does not contain downloaded Workshop mod folders, copied weapon assets, game classes, personal saves, old-map continuity or character ownership migration. ZombieBuddy is downloaded directly from its author’s GitHub release. Better Car Physics components come from your Steam download.

## Validation

The installation/update/rollback fixtures run on Windows in CI; the packaged executable and GUI startup are checked there too. The release recipes were reconstructed locally and compared byte-for-byte with the reconciled setup. All eight Extras/Xen/adjustment combinations have valid recipe dependencies. This does not establish an actual Windows game launch or multiplayer compatibility.

The executable is currently unsigned. Source code and the integration manifest are available here.

## Development

Requires Python 3.12 or newer, with Tk for the GUI. No third-party runtime Python dependencies.

```
python -m unittest discover -p "test_*.py" -v
python knox_setup.py --self-test
python knox_setup.py
```

`integration.json` is exported from the private maintenance repository after upstream reconciliation. It is input- and output-hash guarded. The private repository and its saves/backups are not published here.
