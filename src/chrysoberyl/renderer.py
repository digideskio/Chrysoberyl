# encoding: UTF-8

"""Functions and classes for rendering Chrysoberyl data as HTML pages.

"""

import codecs
import os
import re

from jinja2 import BaseLoader, Environment
from jinja2.exceptions import TemplateNotFound
import markdown

from chrysoberyl.loader import load_docs
from chrysoberyl.transformer import (
    filekey, sleek_key, pathname2url, markdown_contents
)


DOCUMENTATION = None


class Loader(BaseLoader):
    def __init__(self, template_dirs):
        self.template_dirs = template_dirs

    def get_source(self, environment, filename):
        found_path = None
        for template_dir in self.template_dirs:
            path = os.path.join(template_dir, filename)
            if os.path.exists(path):
                found_path = path
                break
        if found_path is None:
            raise TemplateNotFound(filename)
        with open(found_path, 'r') as f:
            source = f.read().decode('utf-8')
        return source, found_path, lambda: True


class Renderer(object):
    """Object which renders Chrysoberyl data as HTML pages.

    """
    def __init__(self, universe, space, template_dirs, output_dir, clone_dir,
                 sleek_node_links, docs_filename):
        self.universe = universe
        self.space = space
        self.template_dirs = template_dirs
        assert isinstance(template_dirs, list)
        self.output_dir = output_dir
        self.clone_dir = clone_dir
        self.sleek_node_links = sleek_node_links
        self.jinja2_env = Environment(loader=Loader(self.template_dirs))
        self.docs_filename = docs_filename

    def render(self, template, output_filename, context):
        """Low-level method to render a given template."""
        with codecs.open(output_filename, 'w', 'utf-8') as html:
            html.write(template.render(context))

    def get_template(self, key):
        """Helper method to retrieve the appropriate template for the given
        key.

        If the node is a type, look first for a template called
        type_[key].html, in ALL the template directories.  If found, load it
        as the template.  If not found, load type.html as the template.

        Look for a template named [key].html in ALL the template directories.
        If found, use it as the template.

        If no template yet, look for a template named [type].html in ALL the
        template directories.  If found, use it as the template.

        If no template yet, use base.html as the template.

        Note that this logic is not in the template loader, because it resolves
        keys to filenames, and is not applicable during {% extends foo %}.

        """
        node = self.universe.get_node(key)
        # Mercurial can't handle filenames containing ':' on Windows, so:
        key_filename = re.sub(':', '_', filekey(key))

        def find_template(filename):
            for template_dir in self.template_dirs:
                full_filename = os.path.join(template_dir, filename)
                if os.path.exists(full_filename):
                    return full_filename
            return None

        if node['type'] == 'type':
            type_filename = 'type_' + key_filename
            if find_template(type_filename):
                return self.jinja2_env.get_template(type_filename)
            else:
                return self.jinja2_env.get_template('type.html')

        if find_template(key_filename):
            return self.jinja2_env.get_template(key_filename)

        type_filename = filekey(node['type'])
        if find_template(type_filename):
            return self.jinja2_env.get_template(type_filename)

        return self.jinja2_env.get_template('base.html')

    def render_node(self, key, node):
        """Render the given Chrysoberyl node (with the given key) as an HTML
        document.

        """
        context = node.copy()
        context['key'] = key
        context['space'] = self.space
        context['sleek_key'] = sleek_key
        context['pathname2url'] = pathname2url

        # Context functions.  Being nested functions of render_node lets
        # them easily access (close over) the current node and its key.

        def expose(fun):
            context[fun.__name__] = fun
            return fun

        @expose
        def get_node(key=key):
            return self.universe.get_node(key)

        @expose
        def md2html(field_contents, prefix=None, fixed=False):
            if fixed:
                md = '\n'.join(
                    ['    ' + l for l in field_contents.split('\n')]
                )
                return markdown.markdown(md)
            else:
                return markdown_contents(field_contents, prefix=prefix)

        @expose
        def base_key(key=key):
            """Returns the 'base' part of the key, that is, with the medium,
            ('(HTML5)', etc), removed.

            """
            if key.endswith(' (HTML5)'):
                return key[:-8]
            if key.endswith(' (Applet)'):
                return key[:-9]
            if key.endswith(' (JaC64)'):
                return key[:-8]
            if key.endswith(' (v86)'):
                return key[:-6]
            return key

        @expose
        def key_ext(key=key):
            """Returns the 'extension' part of the key, that is, the medium,
            ('(HTML5)', etc).

            """
            if key.endswith(' (HTML5)'):
                return 'HTML5'
            if key.endswith(' (Applet)'):
                return 'Applet'
            if key.endswith(' (JaC64)'):
                return 'JaC64'
            if key.endswith(' (v86)'):
                return 'v86'
            return ''

        @expose
        def related(relationship, key=key):
            """Return a list of nodes whose attribute named by `relationship`
            contains the given `key`, whether the attribute is a scalar or a
            list.  Comparable to a database join.

            """
            objects = []
            for thing in self.space:
                if self.space[thing].get('hidden', False):
                    continue
                rel = self.space[thing].get(relationship, None)
                if rel is None:
                    continue
                if rel == key:
                    objects.append(thing)
                    continue
                if isinstance(rel, list) and key in rel:
                    objects.append(thing)
                    continue
            return objects

        @expose
        def impls_for_platform(plat_key, key=key):
            impls = []
            for impl in related('implementation-of', key=key):
                node = self.universe.get_node(impl)
                if (node.get('platform', None) == plat_key or
                    node.get('host_platform', None) == plat_key or
                    node.get('target_platform', None) == plat_key):
                    impls.append(impl)
            return impls

        @expose
        def ref_impl(key=key):
            """Find the reference implementation for the given node
            (assumed to be an implementable), which may be None.

            Once determined, this value is cached in the node.

            """
            node = self.universe.get_node(key)
            if '__reference-implementation__' in node:
                return node['__reference-implementation__']
            ref_i = None
            for i in related('implementation-of', key=key):
                if self.universe.get_node(i).get('reference', False):
                    if ref_i is not None:
                        raise ValueError("more than one ref_impl of %s" % key)
                    ref_i = i
            node['__reference-implementation__'] = ref_i
            return ref_i

        @expose
        def ref_dist(key=key):
            """Find the reference distribution for the given node, which is
            assumed to be an implementable.

            If a `defining-distribution` is given, then that is
            the reference distribution.

            Otherwise, if there is a reference implementation, and the
            reference implementation is in more than zero distributions,
            the first such distribution is the reference distribution.

            Otherwise None.

            """
            node = self.universe.get_node(key)
            if 'defining-distribution' in node:
                return node['defining-distribution']

            ref_i = ref_impl(key=key)
            if ref_i is not None:
                if 'in-distributions' in self.universe.get_node(ref_i):
                    return self.universe.get_node(ref_i)['in-distributions'][0]

            return None

        @expose
        def documentation(key=key):
            """Return a list of documentation file names for the given key."""
            global DOCUMENTATION
            if DOCUMENTATION is None:
                DOCUMENTATION = load_docs(self.docs_filename)
            return sorted(DOCUMENTATION.get(key, []))

        @expose
        def github_link(filename, key=key):
            """Return an HTML link to a file in the Github repository
            associated with the given key, which is assumed to be a
            distribution.

            """
            return "https://github.com/%s/blob/master/%s" % (
                pathname2url(self.universe.get_node(key)['github']),
                pathname2url(filename)
            )

        @expose
        def indefart(text):
            """Try to return a reasonable indefinite article to precede the
            given noun phrase.

            """
            # "u" is dicey
            if text.startswith(("a", "e", "i", "o", "u")):
                return "an " + text
            else:
                return "a " + text

        @expose
        def plural(text):
            """Try to return a reasonable pluralized version of the
            given noun phrase.

            """
            if text[-5:] == 'maton':
                return text[:-5] + 'mata'
            if text[-1:] == 's':
                return text + 'es'
            elif text[-1:] == 'y':
                return text[:-1] + 'ies'
            else:
                return text + 's'

        _indefart = indefart
        _plural = plural

        @expose
        def link(key, format="%s", indefart=False, lower=False, plural=False,
                 link_text=None, title=None):
            """Return an HTML link to the node with the given key.

            indefart causes the link text to be preceded by an indefinite
            article.  lower causes the link text to be lowercase.
            plural causes the link text to be pluralized.

            If the node is of a type that suppresses page generation, this
            will raise an exception.  In the future, it may intelligently
            divert to a different node.

            """
            node = self.universe.get_node(key)
            type_ = node['type']
            if self.universe.get_node(type_).get('suppress-page-generation', False):
                raise KeyError('link to non-page (%s) node %s' % (type_, key))
            if link_text is None:
                link_text = key
                if lower:
                    link_text = link_text.lower()
                if indefart:
                    link_text = _indefart(key)
                if plural:
                    link_text = _plural(link_text)
                link_text = format % link_text
            title_attr = ''
            if title is not None:
                title_attr = ' title="%s"' % title
            if self.sleek_node_links:
                href = pathname2url(sleek_key(key))
            else:
                href = pathname2url(filekey(key))
            return '<a href="%s"%s>%s</a>' % (href, title_attr, link_text)

        # not the kind you're probably thinking of
        @expose
        def linked_list(keys, format="%s"):
            """Given a list of keys, return a fragment of HTML containing
            links to nodes with those keys.  The list is formatted in a human-
            readable fashion, with commas, and the word "and" before the
            end.

            """
            if len(keys) == 1:
                return link(keys[0], format=format)
            elif len(keys) == 2:
                return "%s and %s" % (link(keys[0], format=format),
                                      link(keys[1], format=format))
            else:
                front = keys[:-1]
                last = keys[-1]
                return "%s and %s" % (
                    ', '.join([link(f, format=format) for f in front]),
                    link(last, format=format)
                )

        @expose
        def online_buttons(key=key, show_verb_phrase=True):
            html = ''
            for impl in sorted(related('implementation-of', key=key)):
                node = self.universe.get_node(impl)
                if len(node.get('online-locations', [])) > 0:
                    for loc in sorted(node['online-locations']):
                        html += '<a class="button" href="'
                        html += sleek_key(loc)
                        html += '">'
                        mediums = self.universe.get_node(loc)['mediums']
                        medium = None
                        if 'Java applet' in mediums:
                            medium = 'Java applet'
                        elif 'HTML5' in mediums:
                            medium = 'HTML5'
                        else:
                            assert False, 'No good medium in ' + \
                                          ' on '.join(mediums)
                        if show_verb_phrase:
                            if self.universe.get_node(key)['type'] == 'Game':
                                html += 'Play'
                            else:
                                html += 'Try it'
                            html += ' Online (%s)' % medium
                        else:
                            html += medium
                        html += '</a> '
                if node['host_language'] == 'mp3' and 'download-link' in node:
                    html += ('<a class="button" href="%s">Listen (MP3)</a> ' %
                             node['download_link'])
            return html

        @expose
        def online_installations(exhibit_key, key=key):
            if exhibit_key == 'Music Exhibit':
                impls = []
                for thing in data:
                    if (data[thing]['type'] == 'Musical Composition' and
                        "What is this I don't even" in data[thing].get('auspices', []) and
                        data[thing]['development_stage'] not in ('idea', 'work in progress', 'abandoned', 'unfinished', 'lost')):
                        for impl in related('implementation-of', key=thing):
                            if data[impl]['host-language'] == 'mp3':
                                impls.append(impl)
                return sorted(impls)
            elif 'contents' in data[exhibit_key]:
                return data[exhibit_key]['contents']
            else:
                return sorted([t for t in related('type', key=key)
                        if exhibit_key in data[t]['exhibits']])

        @expose
        def strip_outer_p(text):
            match = re.match(
                r'^\s*\<p\>\s*(.*?)\s*\<\/p\>\s*$', text,
                re.DOTALL
            )
            if match:
                return match.group(1)
            return text

        @expose
        def debug(text):
            print
            print text
            print
            return ''

        @expose
        def error(text):
            raise ValueError(text)

        @expose
        def breadcrumbs(key=key):
            """Generate breadcrumbs for the node given by key."""
            # ("This function's more like spaghetti than breadcrumbs,"
            # quips Release Notes Girl.  Captain Compiler responds:
            # "Does that mean we're going to make it open-sauce?  HA, HA")
            TOP = "Chrysoberyl"
            bc = []
            if key != TOP:
                while 'domain' in self.universe.get_node(key):
                    key = self.universe.get_node(key)['domain']
                    if key == TOP:
                        break
                    bc.append(link(key))
                if key != TOP and self.universe.get_node(key)['type'] != 'type':
                    bc.append(link(self.universe.get_node(key)['type'], plural=True))
                bc.append(link(TOP))
            bc.append('<a href="../">catseye.tc</a>')
            bc.reverse()
            return bc

        @expose
        def recommended_implementation(implementable, key=key):
            """Return a node representing the recommended implementation of
            the given key (assumed to be an implementable.)

            """
            node = self.universe.get_node(key)
            if 'recommended-implementation' in node:
                return node['recommended-implementation']
            impls = related('implementation-of', key=implementable)
            if len(impls) == 0:
                return None
            if len(impls) == 1:
                return impls[0]
            candidates = []
            # XXX can we statically check this?
            for impl in impls:
                if 'generally-recommended' in self.universe.get_node(impl):
                    candidates.append(impl)
            if len(candidates) == 1:
                return candidates[0]
            raise KeyError("Implementable %s has more than one generally "
                           "recommended implementation (under key %s)" %
                           (implementable, key))

        @expose
        def lingography():
            """Return a list of all entries that will be shown on the
            lingography.  This is a bespoke context function, rather than
            a Jinja2 template using related(), because we want to display
            a count of the items in the template.

            """
            languages = []
            types = ('Programming Language', 'Programming Language Family',
                     'Conlang', 'Automaton')
            for thing in self.space:
                node = self.space[thing]
                if (node['type'] in types and
                    'Chris Pressey' in node.get('authors', []) and
                    node.get('development-stage', 'idea') not in \
                        ('idea', 'work in progress') and
                    not node.get('variant-of', None) and
                    (node.get('member-of', None) != 'Funge-98')):
                    languages.append(thing)
            return sorted(languages,
                          key=lambda x: self.space[x]['inception-date'])

        @expose
        def articles():
            """Return a list of all article entries to be shown on the articles
            node.  This is a bespoke context function because we want the
            nodes to be sorted by publication date (and this is an easy way
            to do that.  There might be others.)

            """
            items = []
            for thing in self.space:
                node = self.space[thing]
                if node['type'] == 'Article':
                    items.append(thing)
            return reversed(sorted(
                items,
                key=lambda x: self.space[x]['publication-date']
            ))

        @expose
        def latest_news_item():
            """Returns a key, not a node.

            """
            latest = None
            latest_date = None
            for thing in data:
                node = data[thing]
                if node['type'] == 'Article':
                    if latest_date is None or \
                       node['publication-date'] > latest_date:
                        latest_date = node['publication-date']
                        latest = thing
            return latest

        @expose
        def strftime(date, fmt):
            return date.strftime(fmt)

        template = self.get_template(key)
        basename = filekey(key)
        filename = os.path.join(self.output_dir, basename)
        self.render(template, filename, context)
        # sideways compatibility
        if '_' in basename:
            basename = basename.replace('_', ' ')
            filename = os.path.join(self.output_dir, basename)
            self.render(template, filename, context)

    def render_chrysoberyl_data(self):
        """Render all nodes in the loaded Chrysoberyl data as HTML
        documents.

        """
        count = 0
        for (key, node) in self.space.iteritems():
            type_ = node['type']
            if self.universe.get_node(type_).get('suppress-page-generation', False):
                continue
            self.render_node(key, node)
            count += 1
        print "%d files written." % count
