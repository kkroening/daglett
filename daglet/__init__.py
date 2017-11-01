from __future__ import unicode_literals

from ._utils import get_hash_int
from builtins import object
from collections import defaultdict
import copy


def _arg_kwarg_repr(args=[], kwargs={}):
    items = ['{}'.format(arg) for arg in args]
    items += ['{}={}'.format(key, kwargs[key]) for key in sorted(kwargs)]
    return ', '.join(items)


class Vertex(object):
    """Vertex in a directed-acyclic graph (DAG).

    Hashing:
        Vertices must be hashable, and two vertices are considered to be equivalent if they have the same hash value.

        Vertices are immutable, and the hash should remain constant as a result.  If a vertex with new contents is
        required, create a new vertex and throw the old one away.
    """
    def __init__(self, label=None, parents=[], extra_hash=None):
        for parent in parents:
            if not isinstance(parent, Vertex):
                raise TypeError('Expected Vertex instance; got {}'.format(parent))
        parents = sorted(parents)
        self.__parents = parents
        self.__label = copy.copy(label)
        self.__extra_hash = copy.copy(extra_hash)
        self.__hash = get_hash_int([label, parents, extra_hash])

    @property
    def parents(self):
        return self.__parents

    @property
    def label(self):
        return self.__label

    @property
    def extra_hash(self):
        return self.__extra_hash

    def __hash__(self):
        return self.__hash

    def __lt__(self, other):
        return hash(self) < hash(other)

    def __le__(self, other):
        return hash(self) <= hash(other)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return hash(self) != hash(other)

    def __ge__(self, other):
        return hash(self) >= hash(other)

    def __gt__(self, other):
        return hash(self) > hash(other)

    @property
    def short_hash(self):
        return '{:x}'.format(abs(hash(self)))[:8]

    def get_repr(self, include_hash=True):
        args = []
        if self.__label is not None:
            args.append(repr(self.__label))
        if self.__parents or self.__extra_hash:
            args.append('...')
        ret = 'daglet.Vertex({})'.format(_arg_kwarg_repr(args))
        if include_hash:
            ret = '{} <{}>'.format(ret, self.short_hash)
        return ret

    def __repr__(self):
        return self.get_repr()

    def clone(self, **kwargs):
        base_kwargs = {
            'label': self.__label,
            'parents': self.__parents,
            'extra_hash': self.__extra_hash,
        }
        base_kwargs.update(kwargs)
        return Vertex(**base_kwargs)

    def transplant(self, new_parents):
        """Create a copy of this Vertex with new parent edges."""
        return Vertex(self.__label, new_parents, self.__extra_hash)

    def vertex(self, label=None, extra_hash=None):
        """Create downstream vertex with specified label.

        Example:
            The following example creates a DAG with three vertices connected with two edges (``n1 -> n2 -> n3``):
            ```
            n3 = daglet.Vertex('n1').vertex('n2').vertex('n3')
            ```
        """
        return Vertex(label, [self], extra_hash)


def default_get_parents(x):
    return x.parents


def toposort(objs, parent_func, tree=False):
    marked_objs = set()
    sorted_objs = []

    def visit(obj, child_obj):
        if not tree and obj in marked_objs:
            # TODO: optionally break cycles.
            raise RuntimeError('Graph is not a DAG; recursively encountered {}'.format(obj))

        if tree or obj not in sorted_objs:
            parent_objs = parent_func(obj)

            marked_objs.add(obj)
            for parent_obj in parent_objs:
                visit(parent_obj, obj)
            marked_objs.remove(obj)

            sorted_objs.append(obj)

    unvisited_objs = copy.copy(objs)
    while unvisited_objs:
        obj = unvisited_objs.pop()
        visit(obj, None)
    return sorted_objs


def transform(objs, parent_func, vertex_func=None, edge_func=None, vertex_map={}):
    if vertex_func is None:
        vertex_func = lambda obj, parent_values: None
    if vertex_map is not None:
        old_parent_func = parent_func
        parent_func = lambda x: old_parent_func(x) if x not in vertex_map else []
    if edge_func is None:
        edge_func = lambda parent_obj, obj, parent_value: parent_value

    sorted_objs = toposort(objs, parent_func)

    new_vertex_map = {}
    new_edge_map = {}
    for obj in sorted_objs:
        if obj in vertex_map:
            value = vertex_map[obj]
        else:
            parent_objs = parent_func(obj)
            parent_values = []
            for parent_obj in parent_objs:
                value = edge_func(parent_obj, obj, new_vertex_map[parent_obj])
                new_edge_map[parent_obj, obj] = value
                parent_values.append(value)
            value = vertex_func(obj, parent_values)
        new_vertex_map[obj] = value

    return new_vertex_map, new_edge_map


def transform_vertices(objs, parent_func, vertex_func, vertex_map={}):
    vertex_map, _ = transform(objs, parent_func, vertex_func, None, vertex_map)
    return vertex_map


def transform_edges(objs, parent_func, edge_func):
    _, edge_map = transform(objs, parent_func, None, edge_func)
    return edge_map


def get_parent_map(objs, parent_func):
    sorted_objs = toposort(objs, parent_func)
    parent_map = defaultdict(set)
    for obj in sorted_objs:
        for parent in parent_func(obj):
            parent_map[obj].append(parent)
    return parent_map


def get_child_map(objs, parent_func):
    sorted_objs = toposort(objs, parent_func)
    child_map = defaultdict(set)
    for obj in sorted_objs:
        for parent in parent_func(obj):
            child_map[parent].add(obj)
    return child_map


from .view import view
(view)  # silence linter