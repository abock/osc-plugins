def do_build_product_image (self, subcmd, opts, *args):
    
    # Load OBS package information for this image
    args = parseargs (args)
    packages = findpacs (args)
    if packages == []:
        self.fatal_error ('You must be in an OBS package checkout directory')
    package = packages[0]

    # Change into the package dir and store the cwd back
    os.chdir (package.dir)
    package.dir = '.'

    # Load image configuration and run pre-build checks
    self.load_product_image_rc (package, 'build-product-image.config.py', True)
    self.load_product_image_rc (package, 'build-product-image.config-local.py', False)

    if self.build_product_config.has_key ('build_root'):
        conf.config['build-root'] = self.build_product_config['build_root']
        os.environ['OSC_BUILD_ROOT'] = conf.config['build-root']

    self.check_package (package)
    if self.build_product_config.has_key ('create_iso'):
        self.check_for_iso_support ()
    self.check_for_local_changes (package)
    self.update_package (package)

    if self.build_product_config.has_key ('required_files'):
        for required_file in self.build_product_config['required_files']:
            self.enforce_required_file (required_file)

    if self.build_product_config.has_key ('pre_build_rules'):
        self.run_rule_set ('pre build', self.build_product_config['pre_build_rules'])
    self.build_image (package)
    if self.build_product_config.has_key ('post_build_rules'):
        self.run_rule_set ('post build', self.build_product_config['post_build_rules'])

    self.post_process_build ()


def load_product_image_rc (self, package, config_file, required):
    image_rc_path = os.path.join (os.getcwd (), config_file)
    if not os.path.isfile (image_rc_path):
        if not required:
            return
        self.fatal_error ('There is no config file defined to build a product image: %s' % \
            image_rc_path)
    exec open (image_rc_path).read ()


def check_package (self, package):
    if package.islink ():
        self.fatal_error ('You cannot build a product image from a linked package.')


def check_for_iso_support (self):
    path = '/usr/lib/YaST2/bin/y2mkiso'
    if not os.path.exists (path) or not os.access (path, os.X_OK):
        self.fatal_error ('Can\'t execute /usr/lib/YaST2/bin/y2mkiso.\n'
            'Install yast2-product-creator')

    print 'Updating rescue-dvd-tool from git'
    if os.path.isdir ('rescue-dvd-tool'):
        pwd = os.getcwd ()
        os.chdir ('rescue-dvd-tool')
        self.run_shell ('git pull')
        os.chdir (pwd)
    else:
        self.run_shell ('git clone http://w3.suse.de/~abockover/git/rescue-dvd-tool')


def check_for_local_changes (self, package):
    modified_files = []
    for entry in getStatus ([package]):
        if entry[0] != '?':
            modified_files.append (entry[1:].strip ())
    if not modified_files == []:
        self.fatal_error (
            'A product image cannot be built with local changes.\n'
            'Modified files:\n  - %s' % '\n  - '.join (modified_files))


def update_package (self, package):
    print 'Updating package %s' % package.name
    self.run_shell ('osc --no-keyring up')


def build_image (self, package):
    build_no_verify = ''
    if self.build_product_config.has_key ('build_no_verify'):
        build_no_verify = '--no-verify'
    print 'Building image %s %s' % (package.name, build_no_verify)
    self.run_shell ("""
        osc --no-keyring \
            build \
                --clean \
                %s \
                SUSE_SLE-11_GA i586 \
                suse-moblin-rescue.kiwi
    """ % build_no_verify)


def post_process_build (self):
    import glob
    import shutil

    print 'Post-processing the build...'

    buildroot = conf.config['build-root']
    suse_moblin_release_file = '%s/usr/src/packages/KIWIROOT-oem/etc/SuSE-moblin-release' % buildroot
    usb_file = glob.glob ('%s/usr/src/packages/KIWI-oem/*.install.raw' % buildroot)
    if usb_file == []:
        self.fatal_error ('Could not locate the raw USB image.')
    usb_file = usb_file[0]
    build_id = ''

    if os.path.isfile (suse_moblin_release_file):
        suse_moblin_release = {}
        with open (suse_moblin_release_file, 'r') as fp:
            r = re.compile ('^([A-Z_]+)\s*=\s*"?([A-Za-z0-9\._\- ]+)"?$')
            for line in fp.readlines ():
                line = line.strip ()
                m = r.match (line)
                if m: suse_moblin_release[m.group (1)] = m.group (2)
        try:
            build_id = '%s-%s' % (suse_moblin_release['SUSE_MOBLIN_RELEASE_FLAVOR'],
                suse_moblin_release['SUSE_MOBLIN_BUILD_ID'])
            print 'Found /etc/SuSE-moblin-release, build ID is %s' % build_id
        except:
            pass

    shutil.rmtree ('output', ignore_errors = True)
    os.makedirs ('output', 0755)
    shutil.copy2 (usb_file, os.path.join ('output', '%s.usb.raw' % build_id))

    if self.build_product_config.has_key ('create_iso'):
        self.build_product_config.setdefault ('iso_restore_message',
            'Restoring Linux')
        self.build_product_config.setdefault ('iso_restore_grub_label',
            'Restore Linux')
        self.create_iso (build_id,
            self.build_product_config['iso_restore_message'],
            self.build_product_config['iso_restore_grub_label'])

    self.md5sum_for_directory ('output')

    if self.build_product_config.has_key ('output_location'):
        if not os.path.isdir (self.build_product_config['output_location']):
            os.makedirs (self.build_product_config['output_location'])
        shutil.move ('output', os.path.join (self.build_product_config['output_location'], build_id))
    else:
        shutil.move ('output', build_id)


def create_iso (self, build_id, message, grub_label):
    usb_file = os.path.join ('output', '%s.usb.raw' % build_id)
    iso_file = os.path.join ('output', '%s.iso' % build_id)
    self.run_shell ('rescue-dvd-tool/create-rescue-dvd -m "%s" -g "%s" "%s" "%s"' % \
        (message, grub_label, usb_file, iso_file))


## Prepare Rules ##

def run_rule_set (self, name, rule_set):
    for rule in rule_set:
        print "Running %s rule set for %s" % (name, rule)
        for rule_step in rule_set[rule]:
            self.run_rule_step (rule_step)


def run_rule_step (self, rule_step):
    { 'extract' : self.rule_extract,
      'copy'    : self.rule_copy,
      'archive' : self.rule_archive,
      'remove'  : self.rule_remove,
      'shell'   : self.rule_shell
    } [rule_step[0]] (rule_step[1:])


def rule_extract (self, rule):
    archive = rule[0]
    self.enforce_required_file (archive)
    print ' + extracting %s' % archive
    self.run_shell ('tar xf "%s"' % archive)


def rule_copy (self, rule):
    import glob
    sources = self.iter_flatten (rule[0])
    target = rule[1]
    for source in sources:
        for glob_source in glob.glob (source):
            print ' + copying %s to %s' % (glob_source, target)
            self.run_shell ('cp -a "%s" "%s"' % (glob_source, target))


def rule_archive (self, rule):
    archive = rule[0]
    contents = ''
    for child in self.iter_flatten (rule[1:]):
        contents += ' "%s"' % child
    print ' + archiving %s' % archive
    self.run_shell ('tar cf "%s" %s' % (archive, contents))


def rule_remove (self, rule):
    for target in self.iter_flatten (rule):
        if os.path.exists (target):
            print ' + removing %s' % target
            self.run_shell ('rm -rf -- "%s"' % target)


def rule_shell (self, rule):
    print ' + %s' % rule[0]
    self.run_shell (rule[0])


## Utilities ##

def run_shell (self, command):
    if not os.system (command) == 0:
        self.fatal_error ('command \'%s\' failed to execute' % command)


def fatal_error (self, message):
    print >> sys.stderr, 'Error: %s' % message
    sys.exit (1)


def enforce_required_file (self, required_file):
    if not os.path.isfile (required_file):
        self.fatal_error ('required file %s does not exist' % required_file)


def iter_flatten (self, iterable):
    if not isinstance (iterable, (list, tuple)):
        yield iterable
        return
    it = iter (iterable)
    for e in it:
        if isinstance (e, (list, tuple)):
            for f in self.iter_flatten (e):
                yield f
        else:
            yield e

def md5sum (self, path):
    import hashlib
    with open (path, 'rb') as fp:
        hash = hashlib.md5 ()
        while True:
            block = fp.read (8096)
            if not block:
                break
            hash.update (block)
        return hash.hexdigest ()


def md5sum_for_directory (self, root):
    md5sums = {}
    for path in os.listdir (root):
        full_path = os.path.join (root, path)
        if os.path.isdir (full_path):
            self.md5sum_for_directory (full_path)
            continue
        elif os.path.isfile (full_path) and not path == 'md5sums':
            md5sums[path] = self.md5sum (full_path)
    if not md5sums == {}:
        with open (os.path.join (root, 'md5sums'), 'w+') as fp:
            for path, sum in md5sums.items ():
                fp.write ('%s  %s\n' % (sum, path))
