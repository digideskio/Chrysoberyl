# encoding: UTF-8

import codecs
import os
import re

import yaml
try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from chrysoberyl.util import get_it


def bitbucket_repos(data):
    for key in data:
        if data[key]['type'] != 'Distribution':
            continue
        if 'bitbucket' not in data[key]:
            continue
        (user, repo) = data[key]['bitbucket'].split('/')
        yield (key, user, repo)


def for_each_repo(data, clone_dir, fun):
    cwd = os.getcwd()
    count = 0
    for (distribution, user, repo) in sorted(bitbucket_repos(data)):
        if user != 'catseye':
            print "#-- non-catseye distribution: %s" % \
              (distribution)
            continue
        os.chdir(os.path.join(clone_dir, repo))
        fun(distribution, repo)
        count += 1
    os.chdir(cwd)
    return count


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
    docdict = {}

    def troll_repo(distribution, repo):
        if distribution in ('pibfi distribution',):
            print "#!! Skipping %s" % distribution
            return
        docs = []
        for root, dirnames, filenames in os.walk('.'):
            if root.endswith(".hg"):
                del dirnames[:]
                continue
            for filename in filenames:
                for pattern in DOC_PATTERNS:
                    if re.match(pattern, filename):
                        path = os.path.join(root, filename)[2:]
                        docs.append(path)
                        break
        docdict[distribution] = docs

    count = for_each_repo(data, clone_dir, troll_repo)
    
    docdata = {
        'Documentation Index': {
            'type': 'Metadata',
            'entries': docdict,
        }
    }
    output_filename = os.path.join(data_dir, 'documentation.yaml')
    with codecs.open(output_filename, 'w', 'utf-8') as file:
        file.write('# encoding: UTF-8\n')
        file.write('# AUTOMATICALLY GENERATED BY chrysoberyl.py\n')
        file.write(yaml.dump(docdata, Dumper=Dumper, default_flow_style=False))
    print "Doc lists extracted from %d clones." % count


def survey_repos(data, clone_dir):
    repos = {}

    def survey_repo(distribution, repo):
        print repo
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
                    ((tags['tip'] - tags[latest_tag]), tags['tip'], latest_tag, tags[latest_tag])
        repos[repo] = {
            'dirty': dirty,
            'outgoing': outgoing,
            'tags': tags,
            'latest_tag': latest_tag,
            'due': due,
            'diff': diff,
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
            print
    print '-----'
    print "%d repos checked." % count
