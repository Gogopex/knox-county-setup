# Knox County Vanilla++

My mod setup for a more realistic vanilla++ game. This installer adds the compatibility fixes and adjustments that are missing from the Workshop collections.

**Windows 64-bit, Steam edition, PZ 42.21.0 only. No Python installation needed.** It checks Steam build 25485521 and stops on a different game build. The executable and file operations have been tested on Windows; a full installation and game launch on a gaming PC have not been verified yet.

## Get the mods

- **Required:** [Knox County Vanilla++ Main collection](https://steamcommunity.com/sharedfiles/filedetails/?id=3836683250). Open it in Steam, click **Subscribe to all**, then **Add Only**. This keeps any other subscriptions you already have.
- **Optional:** [Knox County Optional Extras](https://steamcommunity.com/sharedfiles/filedetails/?id=3836684696). This adds the larger music library, extra vehicles and Lifestyle hobbies. Subscribe the same way if you want them.

Subscribing downloads the mods. The installer then builds the selected setup from those files. Downloading Xen does not force you to enable its interface.

## First installation

1. **Install Project Zomboid through Steam.** This release needs version **42.21.0**, shown in the game's main menu. If you have another version, this installer will stop; ask for a matching setup release.
2. **Subscribe to the collections above.** Wait until Steam's Downloads page has finished the Workshop downloads. If you skip Extras, untick that option in the installer too.
3. **Download [the latest Windows ZIP](https://github.com/Gogopex/knox-county-setup/releases/latest).** Choose the file named `KnoxCountySetup-...-windows.zip` under Assets, not GitHub's automatically generated Source code ZIP. Right-click the downloaded ZIP, choose **Extract All**, then open the extracted folder. Keep this folder somewhere convenient.
4. **Close the game and fully exit Steam using Steam > Exit.** Closing Steam's window is not enough. Setup needs Steam closed because it configures the Zomboid launch options.
5. **Run `KnoxCountySetup.exe`.** It should detect Steam automatically, including extra library drives. The default profile folder is fine. Choose:
   - **Music, extra vehicles and Lifestyle:** include Optional Extras. Untick if you did not subscribe to that collection.
   - **Xen's inventory interface:** enable our modified Xen UI. Untick to retain the normal inventory interface.
   - **Our loot, archery, pushing and Lifestyle adjustments:** apply those preferences and offer the Knox County sandbox preset. Compatibility repairs remain enabled either way.
6. **Click Install / Update and confirm.** It checks downloads and patch versions before installing. On the first run, it may open the official ZombieBuddy installer in a separate console window. Wait for **Installation complete**, then **press Enter** to close that window. Our installer then continues. If the console reports an error, keep that error text; do not assume ZombieBuddy installed successfully.
7. **Wait for our manager to say Installed.** Restart Steam and use Project Zomboid's normal **Play** button. Knox County now opens automatically; the manager does not need to stay open. ZombieBuddy can ask you to approve its Java mods on first launch; those are its own prompts.
8. **Start a new Sandbox world.** If you selected our adjustments, choose **Knox County** from the saved sandbox presets. Select your character normally; this package contains no character or existing world.

The executable is unsigned, so Windows may show an unknown-publisher prompt. The [source](https://github.com/Gogopex/knox-county-setup) and `SHA256SUMS.txt` are available with the release. Use the download from this repository; do not disable Windows security to run a copy from elsewhere.

## What it installs

**Steam supplies the upstream mods.** We do not host copies of downloaded Workshop mod folders.

Our manager makes playable copies in `%USERPROFILE%\Zomboid\KnoxCounty\mods`, applies the selected patches, writes that profile's enabled mod list, and seeds the sandbox preset and selected mod preferences. Your usual saves, graphics settings and enabled mod list stay in the usual profile. The new profile starts with its own game settings.

After installation, use **Steam's normal Play button** or your normal Steam game shortcut. The installer adds the Knox County profile argument to Zomboid's Steam launch options for the active account, while preserving unrelated flags. The manager is only needed for installation, updates, checks or restore. New saves go under `%USERPROFILE%\Zomboid\KnoxCounty\Saves`; your usual saves remain in their original folder. Restoring the first installation also returns the previous Steam launch options.

Outside the profile folder, it also sets up:

- **ZombieBuddy:** our manager downloads the author's [official Windows installer from GitHub](https://github.com/zed-0xff/ZombieBuddy/releases/tag/windows_installer) and verifies its SHA-256 before opening it. That installer finds the subscribed [ZombieBuddy Workshop item](https://steamcommunity.com/sharedfiles/filedetails/?id=3619862853), copies `ZombieBuddy.jar` and `zbNative.dll` into the game folder, and adds `-agentlib:zbNative --` to Steam launch options. The Workshop subscription alone does not perform this installation. Our manager checks the resulting runtime files. The bundled installer version is for normal Steam launch; use that launch mode rather than Alternate Launch.
- **Better Car Physics:** our manager copies three engine class overrides from its downloaded Workshop item into the game folder, after checking the supported game build and existing files. Those replacements have transaction backups.
- **Steam launch options:** our manager adds the profile path for the active Steam account, alongside ZombieBuddy's loader option. It backs up the previous value. Restore changes just Zomboid's launch options and keeps unrelated Steam settings. Existing launch flags are retained, including when the upstream ZombieBuddy installer runs.

ZombieBuddy and the physics overrides affect other profiles using the same game installation. The Steam options select which profile opens from Play. Your existing saves stay in their original folder.

See **[Included patches](PATCHES.md)** for the full list, what each changes, and which combinations require them. The manager also has an Included patches link.

The manager has three actions: **Install / Update**, **Check** and **Restore**. The status line shows what is happening and the result; **Copy details** copies the full log when you need help. ZombieBuddy is handled during installation. Launch the game from Steam.

## Updates, Check and Restore

- **Install / Update:** with the game and Steam closed, rebuilds playable copies from the current Steam downloads and applies compatible integration patches. Your selected options are remembered. If an upstream file changed in a way our patch does not recognize, it stops and keeps the installed playable copies. Download a newer integration release when one is available.
- **New releases link:** opens the GitHub download page. Extract its Windows ZIP and run the new executable against the same profile folder. This version does not replace its own running executable automatically.
- **Check:** compares managed mod and engine files, the game build and Steam launch options with the installed record. It checks files, not whether a game session runs correctly.
- **Restore:** with the game and Steam closed, returns the previous managed mods, Better Car Physics files and Zomboid launch options. It refuses edited mod/engine files, keeps your edited preferences and leaves saves alone. It cannot undo world changes made while playing. ZombieBuddy installation and removal are separate; the official version currently downloaded does not offer an uninstall menu.

Backups and receipts are in the profile's `.setup/backups` directory. Keep them for rollback. If installation was interrupted, use Restore before retrying.

Choose your content **before starting a world**. Changing checkboxes does not rewrite an existing world's mod selection or sandbox values. First-install preferences are only written when missing, so updates retain subsequent personal choices.

## If it stops

- **Missing Steam download:** subscribe to the linked item/collection, reopen Steam, finish Downloads, then retry. The error gives the missing item's link.
- **Different game build:** this release is for 42.21.0 only. Use a setup release for your installed game build.
- **An upstream file changed:** our integration needs updating for that mod. Keep the existing installed profile and send the named mod/file with the error.
- **Exit Steam:** use Steam > Exit before Install / Update or Restore. Restart Steam after setup finishes.
- **Permission denied in the game folder:** game-folder components could not be written. Close Steam/the game and check folder permissions before retrying; do not manually copy random DLLs.

## Validation and source

Windows CI runs installation/update/rollback fixtures, builds the executable, and checks the embedded integration data and GUI startup. The 121 exported recipes were reconstructed locally against the reconciled mod sources. All eight Extras/Xen/adjustment combinations have valid recipe dependencies. This is not a claim of a full Windows game load or multiplayer compatibility.

The source version uses Python 3.12+ with Tk and no third-party Python runtime dependencies:

```
python -m unittest discover -p "test_*.py" -v
python knox_setup.py --self-test
python knox_setup.py
```

The integration manifest is exported from the private maintenance repository after upstream reconciliation. That repository, its Workshop cache, patch base files, saves and backups are not published here.
