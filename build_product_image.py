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
    self.load_product_image_rc (package)
    self.check_package (package)
    if self.build_product_config['create_iso']:
        self.check_for_iso_support ()
    self.check_for_local_changes (package)
    self.update_package (package)

    for required_file in self.build_product_config['required_files']:
        self.enforce_required_file (required_file)

    self.run_rule_set ('pre build', self.build_product_config['pre_build_rules'])

    self.build_image (package)

    self.run_rule_set ('post build', self.build_product_config['post_build_rules'])


def load_product_image_rc (self, package):
    image_rc_path = os.path.join (os.getcwd (), 'build-product-image.config.py')
    if not os.path.isfile (image_rc_path):
        self.fatal_error ('There is no product-image.rc.py file defined to build a product image: %s' % \
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
    print 'Building image %s' % package.name
    self.run_shell ("""
        osc --no-keyring \
            build \
                --clean \
                SUSE_SLE-11_GA i586 \
                suse-moblin-rescue.kiwi
    """)


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

