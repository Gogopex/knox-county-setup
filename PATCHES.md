# Included patches

These are changes on top of the subscribed Workshop mods. The installer applies them to its own playable copies, leaving the Steam download directories alone. It checks expected input and output hashes; an unfamiliar upstream revision stops the update instead of receiving an old replacement file.

The full preset contains **121 file operations across 24 mod folders**. That count includes added helpers, mod metadata, sound files and local asset copies, not 121 independent fixes. Upstream mods without our patches are also part of the setup.

## Compatibility and repairs

These stay enabled when their parent mods are selected, even if the gameplay-adjustments checkbox is off.

| Mod / combination | What changes |
|---|---|
| Guns of Marz + Vanilla Weapons Plus + Gunworks + Ammo Maker | Separate conflicting ammo, magazine and stat registrations; preserve the intended models/icons; prevent duplicate loot insertion and a shared weapon-upgrade reset. Asset copies/renames happen locally using the downloaded originals. |
| Guns of Marz | Restore missing item icons. |
| Real Vehicle VFX + Maskarad's Summer Car | Use Summer Car's engine/coolant/misfire state for effects instead of competing fault cues. The adapter handles absent Summer Car data. |
| Real Vehicle VFX + Immersive Snow | Give Snow ownership of its enabled snow/blood tracks while retaining other VFX traces. |
| Real Vehicle VFX | Stop its startup settings save from erasing settings for mods that have not registered yet. |
| Immersive Solar Arrays + LG electricity / power usage | Coordinate appliance draw, supply range and battery drain calculations. Separate solar loot changes are optional below. |
| Jumper Cables + Arcadia RV Interiors | Support transfers from a marine battery to a vehicle, and charging the loose battery from a running vehicle. Account for differing capacities, retain a starter reserve and use a 15% gameplay transfer loss. |
| Manage Containers | Normalize grouped inventory rows before reading containers, fixing the error encountered through Xen item menus. This repair is not limited to Xen. |
| Fancy Handwork | Guard invalid/unbound keyboard entries and remove an overly broad hotbar override, retaining scoped off-hand/music/light behavior. |
| Alice's Weapon Sling | Retain our sling attachment, clothing and hotbar integration. |
| Throw Your Bag Across | Recheck reach, bag identity, ownership and action state; preserve inventory items when placement fails. |
| DAMN library | Fix a stale item reference in mold crafting, retaining the restored item's condition. |
| Animals Eat Corpses | Turn off an accidentally shipped debug mode that accelerated stripping and logged status spam. |
| Project Writing | Reject an attempt to replace a stroke ID owned by another author. |
| Corpse Plow Attachment | Defer registration until its dependencies are available. |
| Dynamic Gear Rattling | Repair rattle hooks and optional hearing propagation. Additional AI hearing remains off by default. |
| Here Goes the Sun | Keep the isometric palette without its competing daylight/climate overrides. |
| Hotbar texture fallback (local addon) | Show a placeholder for missing item textures without losing slots/items. It does not require Xen. |

## Selected features

| Feature | What changes / when it installs |
|---|---|
| Xen inventory interface | Better Sorting categories, nested Nearby sources, dropped-bag handling, container highlighting, resizable item columns, food-state display, wrapped tooltips and recipe-knowledge explanations. The optional camera Java loader remains disabled for this isometric setup. All 19 Xen file operations are omitted when Xen is unticked. |
| Campers + Arcadia interiors | A small local addon registers two additional camper variants with existing Arcadia interior pools. It is enabled only when both the camper fleet and Arcadia's vanilla interior addon are selected. |
| Companion Dogs | Our generic dog behavior/configuration changes and quieter positional bite-contact audio. These are included with the mod; the gameplay-adjustments checkbox does not switch them off. The Steam/offline ownership migration for the original playthrough is omitted. |

Better Sorting remains enabled without Xen. Vehicle mechanics and RV interiors remain in Main when the additional vehicle fleet is omitted. The shared DAMN library is also in Main.

## Gameplay-adjustments checkbox

Turning this on applies:

- **Fletcher:** rarer bows by default and explosive/fire arrows disabled by default.
- **Push Vehicle:** conservative mass defaults and side pushing off by default.
- **Tomb's Wardrobe:** restrained loot additions, original zombie outfit pools and a selected set of pre-July-1993 band-shirt designs.
- **Solar Arrays loot:** rarer salvage and associated defaults. The LG power-accounting integration remains either way.
- **Wind Sway:** the Vanilla wind preset as the initial choice.
- **Lifestyle Practical Cleanup:** if Extras/Lifestyle is also selected, prevent new activity grime/litter, adjust manual cleanup and optimize existing scanning/inventory work. Lifestyle's upstream Handler replacement is reconstructed locally from a patch.
- **Knox County sandbox preset and selected mod preferences:** supplied for new worlds / first installation. Existing worlds' saved sandbox values are not rewritten, and existing personal preferences are retained.

These are preferences and extensions, not all bug fixes. Turning them off uses more upstream defaults; it does not remove the compatibility repairs above. Other included changes, such as the dog audio and isometric lighting profile, remain part of the curated baseline.

## Engine installation

ZombieBuddy and Better Car Physics need files outside the profile's mod directory. [The setup guide explains exactly what is copied and what changes Steam's launch options.](README.md#what-it-installs) The installer checks the supported PZ build before applying engine changes. It also configures the active Steam account so the normal Steam Play button opens Knox County, preserving unrelated launch flags and backing up the previous Zomboid options.

## Left out

- Old-map drawing continuity and character/dog ownership migration from the original save.
- Thermal, wound, decomposition, succession and experimental renderer work outside the selected sharing profile.
- A separate Fluffy Hair repair: the current upstream release already includes that fix.
- Personal saves, character identity, machine-specific launch/memory settings and previously recorded Java-mod approvals.

The complete per-file operations and checksums are in [integration.json](integration.json). Third-party authors retain ownership of their mods; see [NOTICE.md](NOTICE.md) for source/provenance details.
