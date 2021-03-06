# encoding: UTF-8

"""Functions to statically check loaded Chrysoberyl data for consistency and
completeness.

"""

from datetime import datetime
import re

from chrysoberyl.objects import ApproximateDate


LEGACY_FIELDS = (
    'reference-distribution',
    'online-implementations',
    'ca-definition-link',
    'bitbucket',
    'issue-tracker',
    'has-makefile',
    'distname',
    # 'commentary',
)


def check_scalar_ref(universe, key, node, property, types=None):
    """Check that the given node has the given property (field) and that it
    is a scalar (not a list.)  If types is given, check that the key contained
    in the field refers to a node of one of those types.

    """
    if property not in node:
        raise KeyError("'%s' does not specify a %s" % (key, property))
    value = node[property]
    value_node = universe.get_node(value)
    assert value_node, \
        "'%s' has undefined %s '%s'" % (key, property, value)
    if types is None:
        return
    if value_node['type'] not in types:
        raise KeyError(
            "'%s' has %s '%s' which is a %s, not a %s" %
            (key, property, value, value_node['type'], types)
        )


def check_optional_scalar_ref(universe, key, node, property, types=None):
    """Like check_scalar_ref, but skip if property not present on node."""
    if property in node:
        check_scalar_ref(universe, key, node, property, types=types)


def check_list_ref(universe, key, node, property, types=None):
    """Check that the given node has the given property (field) and that it
    is a list (not a scalar.)  If types is given, check that all keys
    contained in the list refers to a node of one of those types.

    """
    if property not in node:
        raise KeyError(u"'%s' has no %s list" % (key, property))
    assert isinstance(node[property], list), \
        u"'%s' has non-list %s" % (key, property)
    for value in node[property]:
        value_node = universe.get_node(value)
        assert value, \
            u"'%s' has undefined %s '%s'" % \
            (key, property, value)
        if types is not None:
            assert value_node['type'] in types, \
                u"'%s' has %s '%s' which is a %s, not a %s" % (
                    key, property, value, value_node['type'], types)


def check_optional_list_ref(universe, key, node, property, types=None):
    """Like check_list_ref, but skip if property not present on node."""
    if property in node:
        check_list_ref(universe, key, node, property, types=types)


def resolve_internal_links(universe, data, key, property, text):
    """Check that all cross-references (in [[double brackets]]) in the
    text contained in the given property are keys of nodes that exist
    elsewhere in the Chrysoberyl data.

    """
    if text is None:
        return True
    for match in re.finditer(r'\[\[(.*?)\]\]', text):
        link = match.group(1)
        segments = link.split('|')
        thing = segments[0]
        assert universe.get_node(thing), \
            "'%s' mentions undefined '%s' in '%s'" % \
            (key, thing, property)


def check_chrysoberyl_node(universe, data, key, node):
    """Check that the data in the given node is consistent and
    complete.

    Note that this may have side-effects (altering the contents of the
    node.)  `inception-date` fields are converted to ApproximateDate
    objects, and `publication-date` fields are converted to datetime objects.
    The following fields may be set to a default based on the presence of a
    node or field with a similar name:
        `in-distributions`
    Also, `authors` and `auspices` may be inherited from the implementable
    being implemented.

    Based on 'mediums' on an online installation, installation-of and other
    things may be auto-populated.

    """
    # Every node must have a valid type.
    assert 'type' in node, \
        "'%s' does not specify a type" % key
    type_ = node['type']
    assert universe.get_space_key_node(type_), \
        "'%s' specifies undefined type '%s'" % (key, type_)
    type_node = universe.get_node(type_)
    assert type_node.get('type') == 'type', \
        "'%s' has bad type '%s'" % (key, type_node)

    # Every node may have some of these.
    try:
        if 'inception-date' in node:
            assert node['inception-date'] != 'Unknown'
            node['inception-date'] = \
                ApproximateDate(str(node['inception-date']))
    except Exception:
        print "'%s' has bad inception-date '%s'" % (
            key, node['inception-date']
        )
        raise
    try:
        if 'article-date' in node:
            assert node['type'] == 'Article'
            node['article-date'] = \
                ApproximateDate(str(node['article-date']))
    except Exception:
        print "'%s' has bad article-date '%s'" % (
            key, node['article-date']
        )
        raise
    try:
        if 'publication-date' in node:
            # Tue, 17 May 2011 23:43:10 GMT
            node['publication-date'] = datetime.strptime(
                str(node['publication-date']), '%a, %d %b %Y %H:%M:%S GMT'
            )
    except Exception:
        print "'%s' has bad publication-date '%s'" % (
            key, node['publication-date']
        )
        raise
    check_optional_scalar_ref(universe, key, node, 'domain')
    check_optional_list_ref(universe, key, node, 'see-also')
    check_optional_scalar_ref(universe, key, node, 'genre')
    check_optional_list_ref(universe, key, node, 'authors',
        types=('Individual', 'Organization'))
    check_optional_list_ref(universe, key, node, 'auspices',
        types=('Organization',))
    check_optional_list_ref(universe, key, node, 'influences')
    # These two fields go together.
    if 'auspices' in node:
        assert 'authors' in node, "auspices but no authors in '%s'" % key
    if 'submitted-to' in node:
        for sub in node['submitted-to']:
            check_scalar_ref(universe, key, sub, 'competition',
                             types=('Competition',))
    if 'images' in node:
        for image in node['images']:
            assert 'url' in image, 'image %r has no url' % image

    # Every node may have these, and they may have internal links.
    description = None
    if 'description' in node:
        description = node['description']
    resolve_internal_links(universe, data, key, 'description', description)
    commentary = None
    if 'commentary' in node:
        commentary = node['commentary']
    resolve_internal_links(universe, data, key, 'commentary', commentary)
    as_a_prerequisite = None
    if 'as-a-prerequisite' in node:
        as_a_prerequisite = node['as-a-prerequisite']
    resolve_internal_links(universe, data, key, 'commentary', as_a_prerequisite)

    # No nodes may have legacy fields.
    for legacy_field in LEGACY_FIELDS:
        assert legacy_field not in node, \
            "legacy field '%s' found in '%s'" % (legacy_field, key)

    check_optional_scalar_ref(universe, key, node, 'development-stage',
                              types=('Development Stage',))

    # On to checking fields specific to different types.

    if type_ == 'Article':
        assert 'publication-date' in node
        assert 'article-type' in node

    if type_ == 'Online Installation':
        node['interactive'] = node.get('interactive', False)
        node['animated'] = node.get('animated', False)
        check_list_ref(
            universe, key, node, 'mediums', types=(
                'Platform', 'Programming Language','Implementation',
                'Music Format', 'Musical Instrument', 'Image Format', 'Medium'
            )
        )

        if 'javascript-urls' in node:
            assert 'javascript-module' in node, key
            for url in node['javascript-urls']:
                assert not url.startswith('../module'), url

        if 'mp3' in node['mediums']:
            if not node.get('installation-of', None):
                node['installation-of'] = key + ' (mp3)'
            node['inline-music-installation'] = True

        check_scalar_ref(universe, key, node, 'installation-of',
                         types=('Implementation',))

    if type_ == 'Distribution':
        assert 'development-stage' not in node, \
          "%s mentions 'development-stage'" % key
        check_optional_list_ref(universe, key, node, 'test-requirements',
                                types=('Programming Language', 'Tool'))

    if type_ == 'Implementation':
        check_list_ref(universe, key, node, 'implementation-of')
        check_optional_scalar_ref(universe, key, node,
                                  'recommended-implementation',
                                  types=('Implementation',))

        # for convenience, bring in the type of the thing being implemented
        # the first thing.  we assume they're all the same type.  but...
        # hey, let's build something that implements both Underload and
        # Zoning Variance #5!
        impl_of_type = data[node['implementation-of'][0]]['type']

        check_scalar_ref(universe, key, node, 'license', types=('License',))
        if 'in-distribution' in node:
            assert 'in-distributions' not in node
            node['in-distributions'] = [node['in-distribution']]
            del node['in-distribution']
        check_optional_list_ref(universe, key, node, 'in-distributions',
                                  types=('Distribution',))
        check_optional_list_ref(universe, key, node, 'prebuilt-for-platforms',
                                  types=('Platform', 'Programming Language'))
        if impl_of_type == 'Musical Composition':
            check_scalar_ref(universe, key, node, 'host-language',
                             types=('Music Format',))
        elif impl_of_type == 'Picture':
            check_scalar_ref(universe, key, node, 'host-language',
                             types=('Image Format',))
        else:
            check_scalar_ref(universe, key, node, 'host-language',
                             types=('Programming Language',))
        check_optional_scalar_ref(universe, key, node, 'host-platform',
                         types=('Platform',))
        # these shouldn't really be needed.  derive, derive!
        # I really don't like that 'Programming Language' is in these
        check_optional_list_ref(universe, key, node, 'build-requirements',
                         types=('Library', 'Tool', 'Programming Language'))
        check_optional_list_ref(universe, key, node, 'run-requirements',
                         types=('Library', 'Tool', 'Programming Language'))

        if impl_of_type == 'Platform':
            check_scalar_ref(universe, key, node, 'implementation-type',
                             types=('Implementation Type',))
            platimpls = ('emulator', 'framework', 'operating system')
            assert node['implementation-type'] in platimpls, \
                "Platform has implementation %s not in %r" % \
                    (key, platimpls)
        elif impl_of_type == 'Programming Language':
            check_scalar_ref(universe, key, node, 'implementation-type',
                             types=('Implementation Type',))
            if node['implementation-type'] == 'compiler':
                check_scalar_ref(universe, key, node, 'target-language',
                                 types=('Programming Language',))
                check_optional_scalar_ref(universe, key, node, 'target-platform',
                                 types=['Platform'])
        else:
            check_optional_scalar_ref(universe, key, node, 'implementation-type',
                             types=('Implementation Type',))

        if 'authors' not in node:
            # TODO: assert there's only one
            pl_node = data[node['implementation-of'][0]]
            node['authors'] = pl_node.get('authors', [])
            node['auspices'] = pl_node.get('auspices', [])

    # All "implementables" (except musical compositions)
    # need to pass these checks.
    # Programming Language Family isn't *directly* implementable
    # but it must pass these checks too.  And gets ref-dist linked
    # to it here too.
    if type_ in ['Game', 'Programming Language', 'Library', 'Tool',
                 'Platform', 'Conlang', 'Electronics Project', 'Gewgaw',
                 'Automaton', 'Programming Language Family', 'Text',
                 'Picture']:
        assert 'build-requirements' not in node
        assert 'run-requirements' not in node
        if type_ != 'Picture':
            check_scalar_ref(universe, key, node, 'development-stage',
                             types=['Development Stage'])
        check_optional_scalar_ref(universe, key, node, 'sample-credit',
                                  'Individual')
        check_optional_scalar_ref(universe, key, node, 'variant-of', type_)
        check_optional_list_ref(universe, key, node, 'online-implementations',
                                types=['Online Installation'])

        # to do this properly we'd need to check ref. impls.
        #if not node.get('no-specification', False):
        #    if ('specification-link' not in node and
        #        'standards-body' not in node):
        #        check_scalar_ref(universe, key, node, 'defining-distribution',
        #                         types=['Distribution'])
        check_optional_scalar_ref(universe, key, node, 'defining-distribution',
                                  types=['Distribution'])

    # alternate constraints for musical pieces (implementables)
    if type_ == 'Musical Composition':
        check_scalar_ref(universe, key, node, 'genre', types=['Genre'])
        check_list_ref(universe, key, node, 'authors')
        check_optional_scalar_ref(universe, key, node, 'composed-on')
        check_optional_scalar_ref(universe, key, node, 'using-software')
        check_scalar_ref(universe, key, node, 'development-stage',
                         types=['Development Stage'])

    # additional constraints for games (implementables)
    if type_ == 'Game':
        check_scalar_ref(universe, key, node, 'genre', types=['Genre'])
        check_optional_scalar_ref(universe, key, node, 'platform',
                                  types=['Platform'])
        check_list_ref(universe, key, node, 'authors')

    # additional constraints for platforms (implementables)
    if type_ == 'Platform':
        check_scalar_ref(universe, key, node, 'native-language',
                         types=['Programming Language'])
        check_list_ref(universe, key, node, 'other-languages',
                       types=['Programming Language'])

    # additional constraints for proglangs (implementables)
    if type_ in ('Programming Language', 'Automaton'):
        check_scalar_ref(universe, key, node, 'genre', types=['Genre'])
        check_list_ref(universe, key, node, 'authors')
        check_list_ref(universe, key, node, 'paradigms',
                       types=('Programming Paradigm',))
        check_optional_scalar_ref(universe, key, node, 'computational-class',
                                  types=('Computational Class',))
        check_optional_scalar_ref(universe, key, node, 'member-of',
                                  types=('Programming Language Family',))

    if type_ == 'Programming Language Family':
        check_scalar_ref(universe, key, node, 'genre', types=['Genre'])

    if type_ == 'Ranking':
        check_list_ref(universe, key, node, 'entries')


def check_chrysoberyl_data(universe, data):
    """Check all nodes in the given dictionary of Chrysoberyl data."""
    count = 0
    for key in data:
        count += 1
        check_chrysoberyl_node(universe, data, key, data[key])
    print "%d nodes checked." % count
