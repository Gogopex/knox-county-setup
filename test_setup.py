import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import knox_setup as k

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Knox County tests ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lib = self.root / 'Steam library with spaces'
        self.game = self.lib / 'steamapps/common/ProjectZomboid'
        self.game.mkdir(parents=True)
        (self.lib / 'steamapps/appmanifest_108600.acf').write_text('"AppState" { "buildid" "123" }')
        (self.game / 'ProjectZomboid64.json').write_text('{"vmArgs": ["-Xmx4g"]}')
        self.source = self.lib / 'steamapps/workshop/content/108600/111/mods/Example'
        self.source.mkdir(parents=True)
        (self.source / 'script.lua').write_bytes(b'first\noriginal\nlast\n')
        (self.source / 'engine.class').write_bytes(b'override')
        (self.game / 'ZombieBuddy.jar').write_bytes(b'jar')
        (self.game / 'zbNative.dll').write_bytes(b'dll')
        acf = self.lib / 'steamapps/workshop/appworkshop_108600.acf'
        acf.write_text('"AppWorkshop" { "WorkshopItemsInstalled" { "111" { "manifest" "one" } } "WorkshopItemDetails" { "111" { "manifest" "one" } } }')
        self.profile = self.root / 'Profile with spaces'
        recipe = {'path':'script.lua','kind':'text','source_folder':'Example','source_path':'script.lua',
                  'input_sha256':k.sha(b'first\noriginal\nlast\n'), 'output_sha256':k.sha(b'first\npatched\nlast\n'),
                  'edits':[[1,2,base64.b64encode(b'patched\n').decode()]]}
        self.manifest = {'version':'0.1.0','game_build':'123','order':['Example'],
                         'mods':[{'folder':'Example','name':'Example','ids':['Example'],'extras':False,'xen':False,
                                  'workshop':'111','upstream_folder':'Example','recipes':[recipe]}],
                         'settings':[{'path':'Lua/prefs.txt','data':base64.b64encode(b'user default').decode(),'sha256':k.sha(b'user default')}],
                         'engine':[{'folder':'Example','source':'engine.class','target':'zombie/engine.class','jar_entry':'zombie/engine.class','sha256':k.sha(b'override')}],
                         'zombiebuddy':{'runtime':{'ZombieBuddy.jar':k.sha(b'jar'),'zbNative.dll':k.sha(b'dll')}}}
        with zipfile.ZipFile(self.game/'projectzomboid.jar','w') as z:z.writestr('zombie/engine.class',b'vanilla')

    def install(self, **kw):
        return k.install(self.manifest,[self.lib],self.game,self.profile,log=lambda _:None,**kw)

    def test_install_update_and_two_restores(self):
        state = self.install()
        self.assertEqual((self.profile/'mods/Example/script.lua').read_bytes(),b'first\npatched\nlast\n')
        self.assertEqual(k.check(self.profile),[])
        self.assertEqual((self.source/'script.lua').read_bytes(),b'first\noriginal\nlast\n')
        (self.profile/'Saves/My world').mkdir(parents=True)
        (self.profile/'Saves/My world/player.db').write_bytes(b'personal save')
        (self.profile/'Lua/prefs.txt').write_bytes(b'my preferences')
        self.install()
        self.assertEqual((self.profile/'Lua/prefs.txt').read_bytes(),b'my preferences')
        k.restore(self.profile)
        self.assertEqual(k.check(self.profile),[])
        # Personal preferences deliberately changed after the first install: restore must refuse first.
        with self.assertRaises(k.SetupError): k.restore(self.profile)
        self.assertTrue((self.profile/'Saves/My world/player.db').exists())
        (self.profile/'Lua/prefs.txt').write_bytes(b'user default')
        k.restore(self.profile)
        self.assertFalse((self.profile/'mods').exists())
        self.assertFalse((self.game/'zombie/engine.class').exists())
        self.assertEqual((self.profile/'Saves/My world/player.db').read_bytes(),b'personal save')
        self.assertEqual((self.game/'ZombieBuddy.jar').read_bytes(),b'jar')

    def test_new_upstream_refuses_and_keeps_installed_release(self):
        self.install()
        before = k.tree_hashes(self.profile/'mods')
        (self.source/'script.lua').write_bytes(b'changed upstream\n')
        with self.assertRaisesRegex(k.SetupError,'upstream file changed'): self.install()
        self.assertEqual(k.tree_hashes(self.profile/'mods'),before)
        self.assertEqual(k.pending_transactions(self.profile),[])

    def test_failed_commit_rolls_back_every_owned_change(self):
        original = k.Transaction.replace
        def fail(tx,target,staged,folder=False):
            original(tx,target,staged,folder)
            if Path(target).name == 'engine.class':raise OSError('injected write failure')
        with mock.patch.object(k.Transaction,'replace',fail):
            with self.assertRaises(OSError):self.install()
        self.assertFalse((self.profile/'mods').exists())
        self.assertFalse((self.game/'zombie/engine.class').exists())
        self.assertEqual(k.pending_transactions(self.profile),[])

    def test_restore_refuses_user_mod_edit_without_partial_changes(self):
        self.install()
        (self.profile/'mods/Example/script.lua').write_bytes(b'user edit')
        before = (self.game/'zombie/engine.class').read_bytes()
        with self.assertRaises(k.SetupError):k.restore(self.profile)
        self.assertEqual((self.game/'zombie/engine.class').read_bytes(),before)
        with self.assertRaisesRegex(k.SetupError,'local edits'):self.install()

    def test_interrupted_transaction_is_recoverable(self):
        self.profile.mkdir()
        tx = k.Transaction(self.profile)
        stage = self.profile/'temporary';stage.mkdir();(stage/'a').write_bytes(b'new')
        tx.replace(self.profile/'mods',stage,True)
        self.assertEqual(k.pending_transactions(self.profile),[tx.path])
        with self.assertRaisesRegex(k.SetupError,'interrupted'):self.install()
        k.restore(self.profile)
        self.assertFalse((self.profile/'mods').exists())

    def test_unsupported_game_and_foreign_engine_override(self):
        (self.lib/'steamapps/appmanifest_108600.acf').write_text('"buildid" "999"')
        with self.assertRaisesRegex(k.SetupError,'supports Project Zomboid'):self.install()
        self.assertFalse((self.profile/'mods').exists())
        (self.lib/'steamapps/appmanifest_108600.acf').write_text('"buildid" "123"')
        p=self.game/'zombie/engine.class';p.parent.mkdir();p.write_bytes(b'other mod')
        with self.assertRaisesRegex(k.SetupError,'Another engine patch'):self.install()
        self.assertEqual(p.read_bytes(),b'other mod')

    def test_engine_vanilla_backup_restored(self):
        p=self.game/'zombie/engine.class';p.parent.mkdir();p.write_bytes(b'vanilla')
        self.install();k.restore(self.profile)
        self.assertEqual(p.read_bytes(),b'vanilla')

    def test_optional_dependency_rules(self):
        m=copy.deepcopy(self.manifest)
        m['mods'] += [{'folder':'Fleet','ids':['Fleet'],'extras':True,'xen':False},
                      {'folder':'Xen','ids':['Xen'],'extras':False,'xen':True},
                      {'folder':'Bridge','ids':['Bridge'],'extras':False,'xen':False,'requires':['Fleet']},
                      {'folder':'Cleanup','ids':['Cleanup'],'extras':True,'xen':False,'adjustments_only':True}]
        self.assertEqual([v['folder'] for v in k.selected(m,False,False,False)],['Example'])
        self.assertEqual([v['folder'] for v in k.selected(m,True,False,False)],['Example','Fleet','Bridge'])

    def test_missing_download_and_manifest_pending(self):
        self.assertEqual(k.find_source([self.lib],self.manifest['mods'][0]),self.source)
        acf=self.lib/'steamapps/workshop/appworkshop_108600.acf'
        acf.write_text(acf.read_text().replace('"manifest" "one" } } }','"manifest" "two" } } }'))
        with self.assertRaisesRegex(k.SetupError,'finish updating'):self.install()

    def test_literal_and_copy_checksums_and_path_escape(self):
        for p in ['../evil','/absolute','C:/evil','x\\..\\evil','file:ads']:
            with self.assertRaises(k.SetupError):k.safe(self.root,p)
        self.assertEqual(k.apply_recipe({'kind':'copy','path':'copy','source_folder':'Example','source_path':'engine.class','input_sha256':k.sha(b'override'),'output_sha256':k.sha(b'override')},{'Example':self.source}),b'override')
        with self.assertRaisesRegex(k.SetupError,'checksum'):
            k.apply_recipe({'kind':'literal','path':'a','data':'YQ==','output_sha256':'bad'}, {})

    def test_second_operation_lock(self):
        with k.installation_lock(self.profile):
            with self.assertRaises(k.SetupError):
                with k.installation_lock(self.profile):pass

if __name__=='__main__':unittest.main()
