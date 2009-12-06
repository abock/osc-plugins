def do_build_product_image (self, subcmd, opts, *args):
    
    # Load OBS package information for this image
    args = parseargs (args)
    packages = findpacs (args)
    if packages == []:
        self.fatal_error ('You must be in an OBS package checkout directory [%s]' % package_dir)
    package = packages[0]

    # Load image configuration and run pre-build checks
    self.load_product_image_rc (package)
    self.check_package (package)
    self.check_for_local_changes (package)

    for required_file in build_product_config['required_files']:
        self.enforce_required_file (required_file)

    for prepare_rule in build_product_config['prepare_rules']:
        print "Preparing %s" % prepare_rule
        for rule_step in build_product_config['prepare_rules'][prepare_rule]:
            self.run_prepare_rule_step (rule_step)


def run_shell (self, command):
    if not os.system (command) == 0:
        raise Exception ('command \'%s\' failed to execute' % command)


def fatal_error (self, message):
    print >> sys.stderr, 'Error: %s' % message
    sys.exit (1)


def enforce_required_file (self, required_file):
    if not os.path.isfile (required_file):
        raise Exception ('required file %s does not exist' % required_file)


def load_product_image_rc (self, package):
    image_rc_path = os.path.join (package.dir, 'product-image.rc.py')
    if not os.path.isfile (image_rc_path):
        self.fatal_error ('There is no product-image.rc.py file defined to build a product image: %s' % \
            image_rc_path)
    exec open (image_rc_path).read ()


def check_package (self, package):
    if package.islink ():
        self.fatal_error ('You cannot build a product image from a linked package.')


def check_for_local_changes (self, package):
    modified_files = []
    for entry in getStatus ([package]):
        if entry[0] != '?':
            modified_files.append (entry[1:].strip ())
    if not modified_files == []:
        self.fatal_error (
            'A product image cannot be built with local changes.\n'
            'Modified files:\n  - %s' % '\n  - '.join (modified_files))


def update_project (self, package_dir):
    return

def run_prepare_rule_step (self, rule_step):
#    try:
        { 'extract' : self.prepare_rule_extract,
          'copy'    : self.prepare_rule_copy,
          'archive' : self.prepare_rule_archive,
          'remove'  : self.prepare_rule_remove
        } [rule_step[0]] (rule_step[1:])
#    except:
#        raise Exception ('Invalid rule action: %s' % rule_step[0])


def prepare_rule_extract (self, rule):
    archive = rule[0]
    self.enforce_required_file (archive)
    print ' + extracting %s' % archive
    self.run_shell ('tar xf "%s"' % archive)


def prepare_rule_copy (self, rule):
    import glob
    sources = self.iter_flatten (rule[0])
    target = rule[1]
    for source in sources:
        for glob_source in glob.glob (source):
            print ' + copying %s to %s' % (glob_source, target)
            self.run_shell ('cp -a "%s" "%s"' % (glob_source, target))


def prepare_rule_archive (self, rule):
    archive = rule[0]
    contents = ''
    for child in self.iter_flatten (rule[1:]):
        contents += ' "%s"' % child
    print ' + archiving %s << %s' % (archive, contents)
    self.run_shell ('tar cf "%s" %s' % (archive, contents))


def prepare_rule_remove (self, rule):
    for target in self.iter_flatten (rule):
        print ' + removing %s...' % target
        self.run_shell ('rm -rf -- "%s"' % target)


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

