# encoding: UTF-8

"""Functions for working with local clones of repositories of distributions
named in Chrysoberyl.

Currently only supports Mercurial repositories hosted on Bitbucket.

"""

import codecs
import os
import re
import sys

import yaml
try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from chrysoberyl.util import get_it


### Utilities ###


def bitbucket_repos(data):
    """Generator which yields information about every Mercurial repository
    on Bitbucket referenced by some distribution in Chrysoberyl.

    Information is a triple of the distribution key, the Bitbucket username,
    and the repository name.

    """
    for key in data:
        if data[key]['type'] != 'Distribution':
            continue
        if 'bitbucket' not in data[key]:
            continue
        (user, repo) = data[key]['bitbucket'].split('/')
        yield (key, user, repo)


def for_each_repo(data, clone_dir, fun):
    """Runs the given function for each local repository clone found, passing
    it the distribution key and the repository name, and first changing into
    the clone directory.

    Returns the number of local repository clones traversed.

    """
    cwd = os.getcwd()
    count = 0
    for (distribution, user, repo) in sorted(bitbucket_repos(data)):
        if user != 'catseye':
            print "#-- non-catseye distribution: %s" % \
              (distribution)
            continue
        os.chdir(os.path.join(clone_dir, repo))
        result = fun(distribution, repo)
        if result != False:
            count += 1
    os.chdir(cwd)
    return count


def get_latest_release_tag(data, repo_name, clone_dir):
    """Given the name of a repository, find the distribution node associated
    with it, and return the tag most recently applied to the repository.

    """
    result = {}

    def find_it(distribution, repo):
        if repo != repo_name:
            return

        latest_tag = None
        for line in get_it("hg tags").split('\n'):
            match = re.match(r'^\s*(\S+)\s+(\d+):(.*?)\s*$', line)
            if match:
                tag = match.group(1)
                if tag != 'tip' and latest_tag is None:
                    latest_tag = tag

        result[repo] = latest_tag

    for_each_repo(data, clone_dir, find_it)

    return result[repo_name]


### Repository-Traversing Commands ###


DOC_PATTERNS = (
    r'^LICENSE$',
    r'^UNLICENSE$',
    r'^README',
    r'^.*?\.html$',
    r'^.*?\.markdown$',
    r'^.*?\.txt$',
    r'^.*?\.lhs$',
)


def troll_docs(data, clone_dir, data_dir):
    """Looks for documentation in local repository clones and writes out
    a files that can be used to update the Documentation nodes in the
    Chrysoberyl data.

    """
    docdict = {}

    def troll_repo(distribution, repo):
        if data[distribution].get('skip-docs', False):
            print "#!! Skipping %s" % distribution
            return
        for root, dirnames, filenames in os.walk('.'):
            if root.endswith(".hg"):
                del dirnames[:]
                continue
            for filename in filenames:
                for pattern in DOC_PATTERNS:
                    if re.match(pattern, filename):
                        path = os.path.join(root, filename)[2:]
                        docdict[distribution + '/' + path] = {
                            'type': 'Document',
                            'filename': path,
                            'distribution': distribution,
                        }
                        break

    count = for_each_repo(data, clone_dir, troll_repo)

    #output_filename = os.path.join(data_dir, 'documentation.yaml')
    #with codecs.open(output_filename, 'w', 'utf-8') as file:
    file = sys.stdout
    file.write('# encoding: UTF-8\n')
    file.write('# AUTOMATICALLY GENERATED BY chrysoberyl.py\n')
    file.write(yaml.dump(docdict, Dumper=Dumper, default_flow_style=False))
    #print "Doc lists extracted from %d clones." % count


def survey_repos(data, clone_dir):
    """Generates a report summarizing various properties of the local
    repository clones for distributions in Chrysoberyl.

    """
    repos = {}

    def survey_repo(distribution, repo):
        print repo
        has_modern_name = False
        for release in data[distribution]['releases']:
            distfile_name = {
              'pl-goto-.net': 'pl-goto.net',
            }.get(repo, repo)
            modern_name = "%s-%s-%s" % (
                repo, release['version'], release['revision']
            )
            if modern_name in release['url']:
                has_modern_name = True
                break
        dirty = get_it("hg st")
        #outgoing = get_it("hg out")
        outgoing = ''
        if 'no changes found' in outgoing:
            outgoing = ''
        tags = {}
        latest_tag = None
        for line in get_it("hg tags").split('\n'):
            match = re.match(r'^\s*(\S+)\s+(\d+):(.*?)\s*$', line)
            if match:
                tag = match.group(1)
                tags[tag] = int(match.group(2))
                if tag != 'tip' and latest_tag is None:
                    latest_tag = tag
        due = ''
        diff = ''
        if latest_tag is None:
            due = 'NEVER RELEASED'
        else:
            diff = get_it('hg diff -r %s -r tip -X .hgtags' % latest_tag)
            if not diff:
                due = ''
            else:
                due = "%d changesets (tip=%d, %s=%d)" % \
                    ((tags['tip'] - tags[latest_tag]), tags['tip'],
                     latest_tag, tags[latest_tag])
        repos[repo] = {
            'dirty': dirty,
            'outgoing': outgoing,
            'tags': tags,
            'latest_tag': latest_tag,
            'due': due,
            'diff': diff,
            'has_modern_name': has_modern_name,
        }

    count = for_each_repo(data, clone_dir, survey_repo)

    print '-----'
    for repo in sorted(repos.keys()):
        r = repos[repo]
        if r['dirty'] or r['outgoing'] or r['due']:
            print repo
            if r['dirty']:
                print r['dirty']
            if r['outgoing']:
                print r['outgoing']
            #print r['tags']
            #print len(r['diff'])
            if r['due']:
                print "  DUE:", r['due']
            if r['due'] != 'NEVER RELEASED' and not r['has_modern_name']:
                print "  DUE: has no modernly-named distfile"
            print
    print '-----'
    print "%d repos checked." % count


def test_repos(data, clone_dir):
    """STUB"""

    def test_repo(distribution, repo):
        print repo
        print get_it("grep -rI falderal .")

    for_each_repo(data, clone_dir, test_repo)


OK_ROOT_FILES = (
    'LICENSE', 'UNLICENSE',
    'README.markdown', 'TODO.markdown', 'HISTORY.markdown',
    'test.sh', 'clean.sh',
    'make.sh', 'make-cygwin.sh', 'Makefile',
    '.hgtags', '.hgignore', '.gitignore',
)
OK_ROOT_DIRS = (
    'bin', 'contrib', 'demo', 'dialect',
    'disk', 'doc', 'ebin', 'eg', 'images',
    'impl', 'lib', 'priv', 'script',
    'src', 'tests',
    '.hg',
)


def lint_dists(data, clone_dir, host_language):
    """Check that the layouts of distributions conform to the
    distribution organization guidelines.

    """
    problems = {}

    def lint_repo(distribution, repo):
        problems[distribution] = []
        show_it = True
        if host_language is not None:
            show_it = False
            for key in data:
                if data[key]['type'] != 'Implementation':
                    continue
                if distribution in data[key].get('in-distributions', []):
                    if data[key]['host-language'] == host_language:
                        show_it = True
                        break
        if not show_it:
            return False
        # Begin linting
        if not os.path.exists('README.markdown'):
            problems[distribution].append("No README.markdown")
        if not os.path.exists('LICENSE') and not os.path.exists('UNLICENSE'):
            problems[distribution].append("No LICENSE or UNLICENSE")
        if os.path.exists('LICENSE') and os.path.exists('UNLICENSE'):
            problems[distribution].append("Both LICENSE and UNLICENSE")
        for root, dirnames, filenames in os.walk('.'):
            if root.endswith(".hg"):
                del dirnames[:]
                continue
            if root == '.':
                root_files = []
                for filename in filenames:
                    if filename not in OK_ROOT_FILES:
                        root_files.append(filename)
                if root_files:
                    problems[distribution].append(
                        "Junk files in root: %s" % root_files
                    )

                root_dirs = []
                for dirname in dirnames:
                    if dirname not in OK_ROOT_DIRS:
                        root_dirs.append(dirname)
                if root_dirs:
                    problems[distribution].append(
                        "Junk dirs in root: %s" % root_dirs
                    )

    count = for_each_repo(data, clone_dir, lint_repo)

    problematic_count = 0
    for d in sorted(problems.keys()):
        if not problems[d]:
            continue
        print d
        print '-' * len(d)
        print
        for problem in problems[d]:
            print "* %s" % problem
        print
        problematic_count += 1

    print "Linted %d clones, problems in %d of them." % (
        count, problematic_count
    )
