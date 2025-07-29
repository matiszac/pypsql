from __future__ import annotations
from typing import Literal, Any, Iterable
from dataclasses import dataclass, field, InitVar
from collections import defaultdict



class AliasManager:
    def __init__(self):
        self._aliases: dict[Select | Inner, str] = {}
        self._nodes: list[Select | Inner] = []
        self._table_ref_count: dict[Table, int] = defaultdict(int)

    def register_alias(self, node: Select | Inner):
        if not isinstance(node, (Select, Inner)):
            raise TypeError(f'Invalid AliasManage node type when registering alias: {type(node).__name__}')
        table: Table = node.calling_table if isinstance(node, Select) else node.inner_select.calling_table
        self._table_ref_count[table] += 1
        n = table.name.lower()
        self._aliases[node] = f'{n[0]}{n[len(n)//2]}{n[-1]}{self._table_ref_count[table]}'
        # slightly redundent when compared to astnodes
        # maybe we can merge the context manager with the alias manager and the astnode list.
        self._nodes.append(node)
    
    def get_alias(self, node: Select | Inner) -> str:
        try:
            return self._aliases[node]
        except KeyError:
            raise ValueError(f"Unregistered node: {node!r}")
        
    def merge(self, other: AliasManager):
        for node in other._nodes:
            self.register_alias(node)
            node.alias_manager = self
        other._aliases = None
        other._nodes = None
        other._table_ref_count = None


class SQLContext:
    def __init__(self):
        self._count = 0 # for posgres params, future impl, not really used atm
        self.params: list[Any] = []
        
    def next_placeholder(self) -> str:
        self._count += 1
        return '?'


@dataclass(frozen=True, slots=True)
class ASTNode:
    syntax: Literal['select', 'where', 'group', 'order', 'inner', 'on']
    node: Select | Inner

    def __post_init__(self):
        if not isinstance(self.syntax, str):
            raise TypeError(f'Invalid ASTNode syntax type: {type(self.syntax).__name__}')
        if self.syntax not in ('select', 'where', 'group', 'order', 'inner', 'on'):
            raise ValueError(f'Invalid ASTNode syntax: {self.syntax}')
        if not isinstance(self.node, (Select, Inner)):
            raise TypeError(f'Invalid ASTNode node type: {type(self.node).__name__}')
        

@dataclass(frozen=True, slots=True)
class Filter:
    field: Field
    comp_op: Literal['=', '!=', '>', '>=', '<', '<=']
    value: Any
    origin: Select | Inner = field(default=None, init=False)

    def set_origin(self, origin: Select | Inner) -> None:
        if not isinstance(origin, (Select, Inner)):
            raise TypeError(f'Invalid Filter origin type: {type(origin).__name__}')
        object.__setattr__(self, 'origin', origin)


@dataclass(frozen=True, slots=True)
class Order:
    field: Field
    direction: Literal['ASC', 'DESC']

    def __post_init__(self):
        if not isinstance(self.field, Field):
            raise TypeError(f'Invalid Order field type: {type(self.field).__name__}')
        if self.direction not in ('ASC', 'DESC'):
            raise ValueError(f'Invalid Order direction: {self.direction}')
        

@dataclass(frozen=True, slots=True)
class Field:
    name: str
    type: Literal['int', 'decimal', 'text']
    table: Table
    
    create_variations: InitVar[bool] = True
    
    MAX: MaxField = field(init=False)
    MIN: MinField = field(init=False)
    ASC: Order = field(init=False)
    DESC: Order = field(init=False)

    def __post_init__(self, create_variations: bool):
        if self.type not in ('int', 'decimal', 'text'):
            raise ValueError(f'Invalid Field type: {self.type}')
        if not isinstance(self.table, Table):
            raise ValueError(f'Invalid Field table: {self.table}')
        
        if create_variations:
            object.__setattr__(self, 'MAX', MaxField.from_original(self))
            object.__setattr__(self, 'MIN', MinField.from_original(self))
        else:
            object.__setattr__(self, 'MAX', None)
            object.__setattr__(self, 'MIN', None)

        object.__setattr__(self, 'ASC', Order(self, 'ASC'))
        object.__setattr__(self, 'DESC', Order(self, 'DESC'))

    def __eq__(self, other) -> Filter:
        return Filter(self, '=', other)
    def __ne__(self, other) -> Filter:
        return Filter(self, '!=', other)
    def __lt__(self, other) -> Filter:
        return Filter(self, '<', other)
    def __le__(self, other) -> Filter:
        return Filter(self, '<=', other)
    def __gt__(self, other) -> Filter:
        return Filter(self, '>', other)
    def __ge__(self, other) -> Filter:
        return Filter(self, '>=', other)
    
    def __hash__(self):
        return hash((self.name, self.table))
    
    def is_equal(self, field: Field) -> bool:
        return (
            isinstance(field, Field) and
            self.name == field.name and
            self.table == field.table
        )
    
    def is_in(self, fields: Iterable[Field]) -> bool:
        return any(self.is_equal(f) for f in fields)
    
    def resolve(self, alias: str):
        if isinstance(self, MaxField):
            return f'MAX({alias}.{self.original.name}) AS {alias}.{self.name}'
        if isinstance(self, MinField):
            return f'MIN({alias}.{self.original.name}) AS {alias}.{self.name}'
        if isinstance(self, Field):
            return f'{alias}.{self.name}'
        raise Exception('Unknown Field Type')

@dataclass(frozen=True, slots=True)
class MaxField(Field):
    original: Field = field(init=False)
    
    @classmethod
    def from_original(cls, original: Field) -> MaxField:
        inst = cls(
            name='Max' + original.name,
            type=original.type,
            table=original.table,
            create_variations=False
        )
        object.__setattr__(inst, 'original', original)
        return inst
    
    
@dataclass(frozen=True, slots=True)
class MinField(Field):
    original: Field = field(init=False)
    
    @classmethod
    def from_original(cls, original: Field) -> MinField:
        inst = cls(
            name='Min' + original.name,
            type=original.type,
            table=original.table,
            create_variations=False
        )
        object.__setattr__(inst, 'original', original)
        return inst
    

@dataclass(frozen=True, slots=True)
class Table:
    name: str

    def select(self, *fields: Field):
        return Select(self, *fields)


class Select:
    def __init__(self, calling_table: Table, *fields: Field):
        self.calling_table = calling_table
        self.fields = fields

        self.alias_manager: AliasManager = AliasManager()
        self.alias_manager.register_alias(self)
        self.ast_nodes: list[ASTNode] = [ASTNode('select', self)]

        self.wheres = None
        self.group_by = None
        self.order_by = None
        self.join = None

    def inner(self, inner_select: Select) -> Inner:
        self.join = Inner(self, inner_select)
        return self.join
    
    def where(self, *wheres: Filter) -> Select:
        self.wheres = wheres
        for f in self.wheres:
            if self.join is None:
                f.set_origin(self)
                continue
            if f.field.is_in(self.join.inner_select.fields):
                f.set_origin(self.join)
                continue
            if f.field.is_in(self.fields):
                f.set_origin(self)
                continue
            if f.field.table == self.calling_table:
                f.set_origin(self)
                continue
            raise Exception('Cannot resolve filter origin for field: {f.field.name}')
        self.ast_nodes.append(ASTNode('where', self))
        return self
        # join nodes return columns based on inner select or the table it references 
        # ON clauses left = parent select, right = result of join, aka the join node itself
        # WHERE clauses after can either reference the left aka select, or right aka join node results
    
    def group(self, field: Field) -> Select:
        self.group_by = field
        self.ast_nodes.append(ASTNode('group', self))
        return self
    
    def order(self, *orders: Order) -> Select:
        self.order_by = orders
        self.ast_nodes.append(ASTNode('order', self))
        return self
    
    def resolve(self):
        query = 'SELECT '
        if len(self.fields) == 0:
            query += '* '
        else:
            for field in self.fields:
                query += field.resolve(self.alias) + ','
        return query[:-1] + f' FROM {self.calling_table.name} {self.alias}'

# make Join base class and Inner Subclass
class Inner:
    def __init__(self, parent_select: Select, inner_select: Select):
        self.parent_select: Select = parent_select
        self.inner_select: Select = inner_select
        self.ons = []

        self.alias_manager: AliasManager = self.parent_select.alias_manager
        self.alias_manager.register_alias(self)
        self.alias_manager.merge(self.inner_select.alias_manager)
        # ? 
        self.ast_nodes: list[ASTNode] = self.parent_select.ast_nodes
        self.ast_nodes.append(ASTNode('inner', self))
        self.ast_nodes.extend(inner_select.ast_nodes)
        inner_select.ast_nodes = self.ast_nodes

    def on(self, *ons: Filter) -> Select:
        self.ons = ons
        self.ast_nodes.append(ASTNode('on', self))
        return self.parent_select
    

def Query(select: Select):
    query_parts = get_parts(select)
    sql_parts = []
    while query_parts:
        part_t, part_v = next(iter(query_parts.pop().items()))
        if isinstance(part_v, Select):
            sel = 'SELECT\n'
            if len(part_v.fields) == 0:
                sel += '*  '
            else:
                for field in part_v.fields:
                    sel += field.resolve(part_v.alias_manager.get_alias(part_v)) + ', '
                if part_v.join is not None and len(part_v.join.inner_select.fields) > 0:
                    for field in part_v.join.inner_select.fields:
                        if field in part_v.fields:
                            continue
                        if field.is_max and field.original in part_v.fields:
                            continue
                        sel += field.resolve(part_v.join.alias) + ', '
            sel = sel[0:-2] + f'\nFROM\n{part_v.calling_table.name} {part_v.alias_manager.get_alias(part_v)}'
            if part_v.join is not None:
                if isinstance(part_v.join, Inner):
                    j = part_v.join
                    right_alias = j.alias_manager.get_alias(j)
                    left_alias = part_v.alias_manager.get_alias(part_v)
                    sel += f'\nINNER JOIN (\n?\n) {right_alias}\nON\n'
                    for on in j.ons:
                        if isinstance(on.value, Field):
                            sel += (
                                f'{left_alias}.{on.field.name}'
                                f' {on.comp_op} '
                                f'{right_alias}.{on.value.name}'
                                ' AND '
                            )
                        else:
                            pass # to-do
                    sel = sel[0:-4]
            if part_v.wheres is not None:
                sel += '\nWHERE\n'
                for filter in part_v.wheres:
                    alias = part_v.alias_manager.get_alias(filter.origin)#get_alias(filter.field, part_v, part_v.join)
                    sel += f'{alias}.{filter.field.name} {filter.comp_op} '
                    if filter.field.type == 'int' or filter.field.type == 'decimal':
                        sel += f'{filter.value} AND '
                    elif filter.field.type == 'text':
                        sel += f"'{filter.value}' AND "
                sel = sel[0:-4]
            if part_v.group_by is not None:
                sel += f'\nGROUP BY\n{part_v.alias_manager.get_alias(part_v)}.{part_v.group_by.name}'
            if part_v.order_by is not None:
                sel += '\nORDER BY\n'
                for order in part_v.order_by:
                    alias = get_alias(order.field, part_v, part_v.join)
                    sel += f'{alias}.{order.field.name} {order.direction} AND '
                sel = sel[0:-5]
            if sql_parts:
                before = sql_parts.pop()
                sql_parts.append(sel.replace('?', before))
            else:
                sql_parts.append(sel)
    return sql_parts.pop()+';'


# still used by order nodes
def get_alias(field: Field, select: Select, join: Inner):
    if join is None:
        return select.alias_manager.get_alias(select)
    if field in select.fields:
        return select.alias_manager.get_alias(select)
    if field in join.inner_select.fields:
        return join.alias_manager.get_alias(join)
    
def get_parts(s: Select):
    r_stack = [{ 'select': s }]
    if s.join is None:
        return r_stack
    r_stack.append({ 'join': s.join })
    return r_stack + get_parts(s.join.inner_select)