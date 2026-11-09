"""Knox County setup manager. Standard library only; Windows GUI + portable testable core."""
from __future__ import annotations
import argparse
import base64
from contextlib import contextmanager
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zipfile

VERSION = '0.1.0'
REPOSITORY = 'Gogopex/knox-county-setup'
ROOT = Path(__file__).resolve().parent

class SetupError(Exception):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)

def safe(root, relative):
    # Manifests use forward slashes even on Windows. Reject Windows drive/ADS paths too.
    if not isinstance(relative, str) or '\\' in relative or ':' in relative or not relative:
        raise SetupError('Invalid package path')
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or relative == '.':
        raise SetupError('Invalid package path: ' + relative)
    target = Path(root).joinpath(*p.parts)
    if not target.resolve().is_relative_to(Path(root).resolve()):
        raise SetupError('Path leaves installation directory: ' + relative)
    return target

def tree_hashes(root):
    root = Path(root)
    if not root.exists():
        return {}
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise SetupError('Symbolic links are not supported: ' + str(p))
        if p.is_file():
            result[p.relative_to(root).as_posix()] = file_sha(p)
    return result

def game_closed():
    if sys.platform != 'win32':
        return
    output = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], creationflags=0x08000000).decode(errors='replace')
    for row in csv.reader(output.splitlines()):
        if row and row[0].lower() in {'projectzomboid64.exe', 'projectzomboid32.exe', 'java.exe', 'javaw.exe'}:
            raise SetupError('Close Project Zomboid and Java game processes before changing the setup.')

@contextmanager
def installation_lock(profile):
    profile = Path(profile)
    profile.mkdir(parents=True, exist_ok=True)
    with (profile / '.setup.lock').open('a+b') as f:
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise SetupError('Another setup operation is running.') from e
        try:
            yield
        finally:
            f.seek(0)
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)

def discover_steam():
    candidates = []
    if sys.platform == 'win32':
        import winreg
        for hive, key, name in [(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                                (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')]:
            try:
                with winreg.OpenKey(hive, key) as k:
                    candidates.append(Path(winreg.QueryValueEx(k, name)[0]))
            except OSError:
                pass
        candidates.extend(Path(os.environ.get(k, 'C:/')) / 'Steam' for k in ['ProgramFiles(x86)', 'ProgramFiles'])
    for p in candidates:
        if (p / 'steam.exe').is_file():
            return p
    raise SetupError('Steam was not found. Choose its installation folder.')

def library_paths(steam):
    steam = Path(steam)
    paths = [steam]
    vdf = steam / 'steamapps/libraryfolders.vdf'
    if vdf.exists():
        for value in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding='utf-8', errors='replace')):
            path = Path(value.replace('\\\\', '\\'))
            if path not in paths:
                paths.append(path)
    return paths

def find_game(libraries):
    for p in libraries:
        game = p / 'steamapps/common/ProjectZomboid'
        if (game / 'ProjectZomboid64.json').is_file():
            return game
    raise SetupError('Project Zomboid was not found in the Steam libraries.')

def find_source(libraries, mod):
    for lib in libraries:
        item = lib / 'steamapps/workshop/content/108600' / mod['workshop']
        downloading = lib / 'steamapps/workshop/downloads/108600' / mod['workshop']
        if downloading.is_dir() and any(downloading.iterdir()):
            raise SetupError('Wait for Steam to finish downloading ' + mod['name'] + '.')
        source = safe(item / 'mods', mod['upstream_folder'])
        if not source.is_dir():
            continue
        # Never consume partial/stale item content while Steam is replacing it.
        acf = lib / 'steamapps/workshop/appworkshop_108600.acf'
        if acf.exists():
            text = acf.read_text(errors='replace')
            section = text.split('"WorkshopItemsInstalled"', 1)
            installed = re.search(r'"' + re.escape(mod['workshop']) + r'"\s*\{([^{}]*)\}', section[-1].split('"WorkshopItemDetails"', 1)[0])
            details = text.split('"WorkshopItemDetails"', 1)
            detail = re.search(r'"' + re.escape(mod['workshop']) + r'"\s*\{([^{}]*)\}', details[-1]) if len(details) == 2 else None
            def field(match, key):
                value = re.search(r'"' + key + r'"\s*"([^"]*)"', match.group(1)) if match else None
                return value.group(1) if value else None
            if not installed or (field(detail, 'manifest') and field(installed, 'manifest') != field(detail, 'manifest')):
                raise SetupError('Wait for Steam to finish updating ' + mod['name'] + '.')
        return source
    raise SetupError('Missing Steam download: ' + mod['name'] + '\nhttps://steamcommunity.com/sharedfiles/filedetails/?id=' + mod['workshop'])

def selected(manifest, extras=True, xen=True, adjustments=True):
    mods = []
    for m in manifest['mods']:
        if m['extras'] and not extras:
            continue
        if m['xen'] and not xen:
            continue
        if m.get('adjustments_only') and not adjustments:
            continue
        mods.append(m)
    while True:
        ids = {v for m in mods for v in m['ids']}
        resolved = [m for m in mods if all(v in ids for v in m.get('requires', []))]
        if len(resolved) == len(mods):
            return mods
        mods = resolved

def apply_recipe(recipe, sources):
    kind = recipe['kind']
    if kind == 'literal':
        data = base64.b64decode(recipe['data'], validate=True)
    else:
        path = safe(sources[recipe['source_folder']], recipe['source_path'])
        data = path.read_bytes()
        if sha(data) != recipe['input_sha256']:
            raise SetupError('An upstream file changed and needs an updated integration patch:\n' + recipe['source_folder'] + '/' + recipe['source_path'] + '\nYour installed setup has not been replaced.')
        if kind == 'text':
            lines = data.splitlines(keepends=True)
            for start, end, encoded in reversed(recipe['edits']):
                if not 0 <= start <= end <= len(lines):
                    raise SetupError('Invalid text patch')
                lines[start:end] = [base64.b64decode(encoded, validate=True)]
            data = b''.join(lines)
        elif kind != 'copy':
            raise SetupError('Unknown integration operation: ' + kind)
    if sha(data) != recipe['output_sha256']:
        raise SetupError('Integration output checksum failed: ' + recipe['path'])
    return data

class Transaction:
    """Durable undo journal. Files are backed up before replacement; interrupted runs are recoverable."""
    def __init__(self, profile):
        self.profile = Path(profile)
        self.root = self.profile / '.setup/backups' / (time.strftime('%Y%m%dT%H%M%S') + '-' + str(time.time_ns()))
        self.root.mkdir(parents=True)
        self.path = self.root / 'receipt.json'
        self.record = {'status': 'installing', 'actions': [], 'version': VERSION}
        self.flush()

    def flush(self):
        atomic_json(self.path, self.record)

    def replace(self, target, staged, folder=False, preserve_edits=False):
        target, staged = Path(target), Path(staged)
        backup = self.root / str(len(self.record['actions']))
        before = tree_hashes(target) if folder else (file_sha(target) if target.exists() else None)
        after = tree_hashes(staged) if folder else file_sha(staged)
        action = {'target': str(target.resolve()), 'backup': str(backup.resolve()), 'folder': folder, 'before': before, 'after': after, 'preserve_edits': preserve_edits}
        if target.exists():
            if folder:
                # Same filesystem: backup and profile live together.
                pass
            else:
                shutil.copy2(target, backup)
        self.record['actions'].append(action)
        self.flush()
        target.parent.mkdir(parents=True, exist_ok=True)
        if folder and target.exists():
            os.replace(target, backup)
        if folder:
            os.replace(staged, target)
        else:
            temp = target.with_name(target.name + '.knox-new')
            shutil.copy2(staged, temp)
            os.replace(temp, target)

    def commit(self):
        self.record['status'] = 'installed'
        self.flush()

    @staticmethod
    def restore(path, check=True):
        path = Path(path)
        r = json.loads(path.read_text())
        # Validate every action before restoring any, so a user edit never causes a partial rollback.
        keep = set()
        for a in reversed(r['actions']):
            target, backup = Path(a['target']), Path(a['backup'])
            now = tree_hashes(target) if a['folder'] else (file_sha(target) if target.exists() else None)
            interrupted_swap = a['folder'] and not target.exists() and backup.exists()
            if check and now not in (a['after'], a['before']) and not interrupted_swap:
                if a.get('preserve_edits'):
                    keep.add(str(target)); continue
                raise SetupError('File changed since installation; restore stopped: ' + str(target))
            if a['before'] and not backup.exists() and now != a['before']:
                raise SetupError('Missing restore backup: ' + str(backup))
        for a in reversed(r['actions']):
            target, backup = Path(a['target']), Path(a['backup'])
            if str(target) in keep:
                continue
            now = tree_hashes(target) if a['folder'] else (file_sha(target) if target.exists() else None)
            if now == a['before']:
                continue
            if a['folder']:
                if target.exists():
                    shutil.rmtree(target)
                if backup.exists():
                    os.replace(backup, target)
            elif a['before'] is None:
                target.unlink(missing_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
        r['preserved_preferences'] = sorted(keep)
        r['status'] = 'restored'
        atomic_json(path, r)

def pending_transactions(profile):
    return [p for p in sorted((Path(profile) / '.setup/backups').glob('*/receipt.json'))
            if json.loads(p.read_text()).get('status') == 'installing']

def verify_game_build(game, manifest):
    game = Path(game)
    acf = game.parent.parent / 'appmanifest_108600.acf'
    if not acf.exists() or not re.search(r'"buildid"\s+"' + re.escape(manifest['game_build']) + '"', acf.read_text()):
        raise SetupError('This release supports Project Zomboid build ' + manifest['game_build'] + ' (42.21.0). Choose that Steam branch or wait for an updated setup release.')


def game_actions(game, sources, manifest, stage):
    game, stage = Path(game), Path(stage)
    verify_game_build(game, manifest)
    actions = []
    for i, a in enumerate(manifest['engine']):
        source = safe(sources[a['folder']], a['source'])
        if file_sha(source) != a['sha256']:
            raise SetupError('Engine component updated upstream: ' + a['source'] + '. An integration update is needed.')
        target = safe(game, a['target'])
        # BCP overrides may replace only native vanilla bytes or our known override bytes.
        if a.get('jar_entry') and target.exists() and file_sha(target) != a['sha256']:
            with zipfile.ZipFile(game / 'projectzomboid.jar') as z:
                original = sha(z.read(a['jar_entry']))
            if file_sha(target) != original:
                raise SetupError('Another engine patch occupies ' + a['target'] + '; nothing replaced.')
        if not target.exists() or file_sha(target) != a['sha256']:
            actions.append((target, source))
    # ZombieBuddy's official GitHub installer owns its runtime and launcher configuration.
    for filename, expected in manifest['zombiebuddy']['runtime'].items():
        runtime = game / filename
        if not runtime.is_file() or file_sha(runtime) != expected:
            raise SetupError('Run Set up ZombieBuddy first, then Install / Update.')
    return actions

def preflight(manifest, libraries, extras=True, xen=True, adjustments=True):
    mods = selected(manifest, extras, xen, adjustments)
    sources = {m['folder']: find_source(libraries, m) for m in mods if m.get('workshop')}
    for m in mods:
        for pin in m.get('input_pins', []):
            if file_sha(safe(sources[pin['folder']], pin['path'])) != pin['sha256']:
                raise SetupError('A compatibility hook needs review after an upstream change: ' + pin['folder'] + '/' + pin['path'])
        for recipe in m.get('recipes', []):
            if not recipe.get('adjustment') or adjustments:
                apply_recipe(recipe, sources)
    for a in manifest['engine']:
        if file_sha(safe(sources[a['folder']], a['source'])) != a['sha256']:
            raise SetupError('An engine component changed upstream. An integration release is needed.')
    # Check Workshop runtime inputs before invoking the external GitHub installer.
    if 'ZombieBuddy' in sources:
        for name, expected in manifest['zombiebuddy']['runtime'].items():
            if file_sha(sources['ZombieBuddy'] / 'libs' / name) != expected:
                raise SetupError('ZombieBuddy changed upstream. An integration release is needed.')
    return mods, sources


def install(manifest, libraries, game, profile, extras=True, xen=True, adjustments=True, log=print, engine=True):
    profile = Path(profile).resolve()
    with installation_lock(profile):
        game_closed()
        if pending_transactions(profile):
            raise SetupError('An interrupted installation needs Restore before trying again.')
        if engine:
            verify_game_build(game, manifest)
        mods, sources = preflight(manifest, libraries, extras, xen, adjustments)
        old_state = profile / '.setup/state.json'
        if not old_state.exists() and (profile / 'Saves').exists():
            raise SetupError('Choose a new Knox County profile directory, separate from existing saves.')
        if (profile / 'mods').exists() and not old_state.exists():
            raise SetupError('The chosen profile already has mods and is not managed by this installer. Choose an empty profile directory.')
        if old_state.exists():
            state = json.loads(old_state.read_text())
            current = tree_hashes(profile / 'mods')
            previous = dict(state['mod_hashes'])
            # The game may rewrite its selection file during normal use. Installer options own the next selection.
            current.pop('default.txt', None); previous.pop('default.txt', None)
            if current != previous:
                raise SetupError('Managed mod files have local edits. Keep a copy or restore them before updating.')
        stage = Path(tempfile.mkdtemp(prefix='.knox-stage-', dir=profile))
        tx = None
        try:
            dest = stage / 'mods'; dest.mkdir()
            for m in mods:
                log('Preparing ' + m['name'])
                target = safe(dest, m['folder'])
                if m.get('workshop'):
                    shutil.copytree(sources[m['folder']], target, ignore=shutil.ignore_patterns('.DS_Store'))
                else:
                    target.mkdir()
                for recipe in m['recipes']:
                    if recipe.get('adjustment') and not adjustments:
                        continue
                    output = safe(target, recipe['path'])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(apply_recipe(recipe, sources))
            ids = {v for m in mods for v in m['ids']}
            order = [v for v in manifest['order'] if v in ids]
            (dest / 'default.txt').write_text('VERSION = 1,\n\nmods\n{\n' + ''.join('    mod = ' + v + ',\n' for v in order) + '}\n\nmaps\n{\n}\n', encoding='utf-8')
            external = game_actions(game, sources, manifest, stage) if engine else []
            seed = stage / 'seed'; seed.mkdir()
            settings = []
            for recipe in manifest.get('settings', []):
                if recipe.get('adjustment') and not adjustments:
                    continue
                if recipe.get('xen') and not xen:
                    continue
                target = safe(profile, recipe['path'])
                # Seed personal preferences only on first install; later updates retain user choices.
                if not target.exists():
                    data = base64.b64decode(recipe['data'], validate=True)
                    if sha(data) != recipe['sha256']:
                        raise SetupError('Settings checksum failed')
                    src = safe(seed, recipe['path']); src.parent.mkdir(parents=True, exist_ok=True); src.write_bytes(data)
                    settings.append((target, src))
            hashes = tree_hashes(dest)
            game_closed()
            tx = Transaction(profile)
            tx.replace(profile / 'mods', dest, folder=True)
            for target, source in external:
                tx.replace(target, source)
            for target, source in settings:
                tx.replace(target, source, preserve_edits=True)
            state = {'version': manifest['version'], 'options': {'extras': extras, 'xen': xen, 'adjustments': adjustments},
                     'mod_hashes': hashes, 'engine_files': {str(t.resolve()): file_sha(t) for t, _ in external},
                     'receipt': str(tx.path.resolve()), 'game_build': manifest['game_build'], 'game': str(Path(game).resolve())}
            # Include already-correct engine components in integrity checks as well.
            if engine:
                for a in manifest['engine']:
                    state['engine_files'][str(safe(game, a['target']).resolve())] = a['sha256']
                for name, expected in manifest['zombiebuddy']['runtime'].items():
                    state['engine_files'][str((Path(game) / name).resolve())] = expected
            out = stage / 'state.json'; atomic_json(out, state)
            tx.replace(old_state, out)
            tx.commit()
            log('Installed. Saves are in this profile; existing saves were not changed.')
            return state
        except Exception:
            if tx:
                Transaction.restore(tx.path, check=False)
            raise
        finally:
            shutil.rmtree(stage, ignore_errors=True)

def check(profile):
    profile = Path(profile)
    state = json.loads((profile / '.setup/state.json').read_text())
    bad = []
    got = tree_hashes(profile / 'mods')
    for p in sorted(got.keys() | state['mod_hashes'].keys()):
        if got.get(p) != state['mod_hashes'].get(p):
            bad.append('mods/' + p)
    for path, expected in state['engine_files'].items():
        if not Path(path).is_file() or file_sha(path) != expected:
            bad.append(path)
    return bad

def restore(profile):
    with installation_lock(profile):
        game_closed()
        receipts = sorted((Path(profile) / '.setup/backups').glob('*/receipt.json'), reverse=True)
        candidate = next((p for p in receipts if json.loads(p.read_text())['status'] in {'installed', 'installing'}), None)
        if not candidate:
            raise SetupError('No installation to restore.')
        Transaction.restore(candidate)
        return str(candidate)

def play(steam, profile):
    if not (Path(profile) / '.setup/state.json').exists():
        raise SetupError('Install the profile first.')
    if pending_transactions(profile):
        raise SetupError('Restore the interrupted installation before playing.')
    state = json.loads((Path(profile) / '.setup/state.json').read_text())
    game = Path(state['game'])
    acf = game.parent.parent / 'appmanifest_108600.acf'
    if not acf.exists() or not re.search(r'"buildid"\s+"' + re.escape(state['game_build']) + '"', acf.read_text()):
        raise SetupError('The game build changed. Check for a compatible setup release before playing.')
    for path, expected in state['engine_files'].items():
        if not Path(path).is_file() or file_sha(path) != expected:
            raise SetupError('An engine component changed. Run Install / Update before playing.')
    subprocess.Popen([str(Path(steam) / 'steam.exe'), '-applaunch', '108600', '-cachedir=' + str(Path(profile).resolve())])

def setup_zombiebuddy(manifest, profile, log=print):
    game_closed()
    info = manifest['zombiebuddy']
    target = Path(profile) / '.setup/downloads' / info['filename']
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or file_sha(target) != info['installer_sha256']:
        log('Downloading the official ZombieBuddy installer from GitHub.')
        req = urllib.request.Request(info['url'], headers={'User-Agent': 'KnoxCountySetup/' + VERSION})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read(32 * 1024 * 1024)
        if sha(data) != info['installer_sha256']:
            raise SetupError('ZombieBuddy installer checksum mismatch; not executed.')
        target.write_bytes(data)
    log('Follow the official installer window. Choose install/update and normal launch. Then return here.')
    subprocess.run([str(target)], check=True, creationflags=0x00000010 if sys.platform == 'win32' else 0)
    log('ZombieBuddy installer finished. Install / Update verifies the runtime files.')


def latest_release():
    req = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + '/releases/latest', headers={'User-Agent': 'KnoxCountySetup/' + VERSION})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read(1024 * 1024))

def gui(smoke=False):
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    app = tk.Tk(); app.title('Knox County Vanilla++'); app.geometry('690x560')
    frame = ttk.Frame(app, padding=20); frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Knox County Vanilla++', font=('Segoe UI', 18)).pack(anchor='w')
    ttk.Label(frame, text='Steam supplies the mods. This installs our fixes and a separate play profile.', wraplength=640).pack(anchor='w', pady=(8, 15))
    try:
        initial = str(discover_steam())
    except SetupError:
        initial = ''
    steam = tk.StringVar(value=initial)
    profile = tk.StringVar(value=str(Path.home() / 'Zomboid/KnoxCounty'))
    for label, value in [('Steam folder', steam), ('Knox County profile', profile)]:
        row = ttk.Frame(frame); row.pack(fill='x', pady=3)
        ttk.Label(row, text=label, width=20).pack(side='left')
        ttk.Entry(row, textvariable=value).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Browse', command=lambda v=value: v.set(filedialog.askdirectory() or v.get())).pack(side='left')
    extras = tk.BooleanVar(value=True); xen = tk.BooleanVar(value=True); adjustments = tk.BooleanVar(value=True)
    def remember_options(*_):
        state = Path(profile.get()) / '.setup/state.json'
        if state.is_file():
            try:
                opts = json.loads(state.read_text())['options']
                extras.set(opts['extras']); xen.set(opts['xen']); adjustments.set(opts['adjustments'])
            except (OSError, ValueError, KeyError):
                pass
    profile.trace_add('write', remember_options)
    remember_options()
    for label, value in [('Music, extra vehicles and Lifestyle', extras), ("Xen's inventory interface", xen), ('Our loot, archery, pushing and Lifestyle adjustments', adjustments)]:
        ttk.Checkbutton(frame, text=label, variable=value).pack(anchor='w', pady=3)
    links = ttk.Frame(frame); links.pack(fill='x', pady=8)
    for title, wid in [('Main collection', '3836683250'), ('Optional extras', '3836684696')]:
        ttk.Button(links, text=title, command=lambda w=wid: webbrowser.open('https://steamcommunity.com/sharedfiles/filedetails/?id=' + w)).pack(side='left', padx=(0, 8))
    ttk.Label(frame, text='Requires PZ 42.21.0. Close the game and finish Steam downloads first.\nInstall / Update opens the official ZombieBuddy installer if needed. Better Car Physics is installed with backups.', wraplength=640).pack(anchor='w', pady=8)
    status = tk.Text(frame, height=8, wrap='word'); status.pack(fill='both', expand=True)
    busy = [False]; buttons = []
    def log(text):
        app.after(0, lambda: (status.insert('end', text + '\n'), status.see('end')))
    def run(fn):
        if busy[0]: return
        busy[0] = True
        for b in buttons: b.configure(state='disabled')
        def work():
            try: fn()
            except Exception as e:
                log(str(e)); app.after(0, lambda msg=str(e): messagebox.showerror('Setup stopped', msg))
            finally:
                busy[0] = False
                app.after(0, lambda: [b.configure(state='normal') for b in buttons])
        threading.Thread(target=work, daemon=False).start()
    def do_install():
        if not messagebox.askokcancel('Install / update', 'This prepares the selected mods and installs Better Car Physics components with backups. If needed, the official GitHub ZombieBuddy installer opens first. Existing saves stay separate. Continue?'): return
        config = (steam.get(), profile.get(), extras.get(), xen.get(), adjustments.get())
        def work():
            manifest = json.loads((ROOT / 'integration.json').read_text())
            libs = library_paths(config[0]); game = find_game(libs)
            # Resolve every patch input before asking the upstream installer to change the game.
            verify_game_build(game, manifest)
            preflight(manifest, libs, *config[2:])
            if any(not (game / name).is_file() or file_sha(game / name) != h for name, h in manifest['zombiebuddy']['runtime'].items()):
                setup_zombiebuddy(manifest, config[1], log)
            install(manifest, libs, game, config[1], *config[2:], log=log)
        run(work)
    def do_zb():
        manifest = json.loads((ROOT / 'integration.json').read_text())
        p = profile.get()
        run(lambda: setup_zombiebuddy(manifest, p, log))
    def do_check():
        p = profile.get()
        def work():
            bad = check(p); log('Files match the installed release.' if not bad else 'Changed/missing files:\n' + '\n'.join(bad[:30]))
        run(work)
    def do_restore():
        p = profile.get()
        if messagebox.askokcancel('Restore', 'Restore the previous managed mods and engine files? Saves remain untouched.'):
            run(lambda: log('Restored: ' + restore(p)))
    def do_update():
        def work():
            release = latest_release()
            if release['tag_name'].lstrip('v') == VERSION:
                log('You have the current setup release. Install / Update also checks your current Steam downloads.')
            else:
                log('New release: ' + release['tag_name'] + '. Download and run it to update this profile.')
                webbrowser.open('https://github.com/' + REPOSITORY + '/releases/latest')
        run(work)
    row = ttk.Frame(frame); row.pack(fill='x', pady=(12, 0))
    for label, fn in [('Install / Update', do_install), ('ZombieBuddy', do_zb), ('Check', do_check), ('Restore', do_restore), ('New releases', do_update), ('Play', lambda: play(steam.get(), profile.get()))]:
        def wrapped(f=fn):
            try: f()
            except Exception as e: messagebox.showerror('Setup stopped', str(e))
        b = ttk.Button(row, text=label, command=wrapped); b.pack(side='left', padx=(0, 5)); buttons.append(b)
    app.protocol('WM_DELETE_WINDOW', lambda: None if busy[0] else app.destroy())
    if smoke: app.after(500, app.destroy)
    app.mainloop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--gui-smoke', action='store_true')
    parser.add_argument('--check', type=Path)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    if args.self_test:
        manifest = json.loads((ROOT / 'integration.json').read_text())
        assert manifest['schema'] == 1 and manifest['version'] == VERSION
        assert len(manifest['mods']) > 100
        for m in manifest['mods']:
            safe(ROOT, m['folder'])
            for recipe in m['recipes']:
                safe(ROOT, recipe['path'])
                if recipe['kind'] == 'literal':
                    assert sha(base64.b64decode(recipe['data'], validate=True)) == recipe['output_sha256']
    elif args.version: print(VERSION)
    elif args.check:
        bad = check(args.check); print(json.dumps(bad)); return int(bool(bad))
    elif args.restore: print(restore(args.restore))
    else: gui(smoke=args.gui_smoke)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
