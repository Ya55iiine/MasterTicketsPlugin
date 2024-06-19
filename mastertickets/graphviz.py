# -*- coding: utf-8 -*-
#
# Copyright (c) 2007-2012 Noah Kantrowitz <noah@coderanger.net>
# Copyright (c) 2013-2016 Ryan J Ollos <ryan.j.ollos@gmail.com>
#
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import itertools
import subprocess

from trac.util.text import to_unicode
from trac.util.translation import _


def _format_options(base_string, options):
    # return u'%s [%s]' % (
    #     base_string,
    #     u', '.join(u'%s="%s"' % x for x in options.items())
    # )
    formatted_options = ', '.join(f'{key}=\"{value}\"' for key, value in options.items())
    return f'{base_string} [{formatted_options}]' 

def _handle_attribute_value(value):
    """Handles converting different attribute values to strings."""
    if isinstance(value, str):
        return value  # Already a string, no conversion needed
    elif hasattr(value, 'iteritems'):
        # Assume it's a dictionary-like object, format as key-value pairs
        return ', '.join(f'{k}={_handle_attribute_value(v)}' for k, v in value.iteritems())
    elif isinstance(value, (list, tuple)):
        # Handle lists and tuples by recursively formatting elements
        return ', '.join(_handle_attribute_value(v) for v in value)
    else:
        return repr(value)

class Edge(dict):
    """Model for an edge in a dot graph."""

    def __init__(self, source, dest, **kwargs):
        self.source = source
        self.dest = dest
        dict.__init__(self, **kwargs)

    def __str__(self):
        # ret = u'%s -> %s' % (self.source.name, self.dest.name)
        # if self:
        #     ret = _format_options(ret, self)
        ret = f'{self.source.name} -> {self.dest.name}'
        options = {str(k): _handle_attribute_value(v) for k, v in self.items()}
        if options:
            ret = _format_options(ret, options)
        return ret

    def __hash__(self):
        return hash(id(self))


class Node(dict):
    """Model for a node in a dot graph."""

    def __init__(self, name, **kwargs):
        self.name = name
        self.edges = []
        dict.__init__(self, **kwargs)

    def __str__(self):
        ret = self.name
        # if self:
        #     ret = _format_options(ret, self)
        options = {str(k): _handle_attribute_value(v) for k, v in self.items()} 
        if options:
            ret = _format_options(ret, options)
        return ret

    def __gt__(self, other):
        """Allow node1 > node2 to add an edge."""
        edge = Edge(self, other)
        self.edges.append(edge)
        other.edges.append(edge)
        return edge

    def __lt__(self, other):
        edge = Edge(other, self)
        self.edges.append(edge)
        other.edges.append(edge)
        return edge

    def __hash__(self):
        return hash(id(self))


class Graph(object):
    """A model object for a graphviz digraph."""

    def __init__(self, name=u'graph', log=None):
        super(Graph, self).__init__()
        self.name = name
        self.log = log
        self.nodes = []
        self._node_map = {}
        self.attributes = {}
        self.edges = []

    def add(self, obj):
        if isinstance(obj, Node):
            self.nodes.append(obj)
            self._node_map[obj.name] = obj
        elif isinstance(obj, Edge):
            self.edges.append(obj)

    def __getitem__(self, key):
        if key not in self._node_map:
            new_node = Node(key)
            self._node_map[key] = new_node
            self.nodes.append(new_node)
        return self._node_map[key]

    def __delitem__(self, key):
        node = self._node_map.pop(key)
        self.nodes.remove(node)

    def __str__(self):
        # edges = []
        # nodes = []

        # memo = set()

        # def process(lst):
        #     for item in lst:
        #         if item in memo:
        #             continue
        #         memo.add(item)

        #         if isinstance(item, Node):
        #             nodes.append(item)
        #             process(item.edges)
        #         elif isinstance(item, Edge):
        #             edges.append(item)
        #             if isinstance(item.source, Node):
        #                 process((item.source,))
        #             if isinstance(item.dest, Node):
        #                 process((item.dest,))

        # process(self.nodes)
        # process(self.edges)

        # lines = [u'digraph "%s" {' % self.name]
        # for att, value in self.attributes.items():
        #     lines.append(u'\t%s="%s";' % (att, value))
        # for obj in itertools.chain(nodes, edges):
        #     lines.append(u'\t%s;' % obj)
        # lines.append(u'}')
        # return u'\n'.join(lines)
        edges = []
        nodes = []

        memo = set()

        def process(lst):
            for item in lst:
                if item in memo:
                    continue
                memo.add(item)

                if isinstance(item, Node):
                    nodes.append(item)
                    process(item.edges)
                elif isinstance(item, Edge):
                    edges.append(item)
                    if isinstance(item.source, Node):
                        process((item.source,))
                    if isinstance(item.dest, Node):
                        process((item.dest,))

        process(self.nodes)
        process(self.edges)

        lines = [f'digraph "{self.name}" {{']
        for att, value in self.attributes.items():
            lines.append(f'\t{att}="{value}";')

        for node in nodes:  # Use nodes from the processed list
            node_attrs = ', '.join(f'{k}="{_handle_attribute_value(v)}"' for k, v in node.items())
            lines.append(f'\t"{node.name}" [{node_attrs}];')

        for edge in edges:  # Use edges from the processed list
            edge_attrs = ', '.join(f'{k}="{_handle_attribute_value(v)}"' for k, v in edge.items() if k not in ('source', 'dest'))
            lines.append(f'\t"{edge.source.name}" -> "{edge.dest.name}" [{edge_attrs}];')

        lines.append('}')
        return '\n'.join(lines)

    def render(self, dot_path='dot', format='png'):
        """Render a dot graph."""
        cmd = [dot_path, '-T%s' % format]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, error = p.communicate(to_unicode(self).encode('utf8'))
        if self.log and error or p.returncode:
            self.log.warning(_("dot command '%(cmd)s' failed with code "
                               "%(rc)s: %(error)s", cmd=' '.join(cmd),
                               rc=p.returncode, error=error))
        return out


if __name__ == '__main__':
    g = Graph()
    root = Node('me')
    root > Node('them')
    root < Node(u'Üs')

    g.add(root)

    print (g.render())
