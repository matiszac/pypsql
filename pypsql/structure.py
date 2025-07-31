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
        
    def placeholder(self, param: Any) -> str:
        self._count += 1
        self.params.append(param)
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

    def to_sql(self, alias_l, alias_r = None, ctx: SQLContext = None) -> str:
        if isinstance(self.value, Field) and alias_r:
            return f'{alias_l}.{self.field.name} {self.comp_op} {alias_r}.{self.value.name}'
        elif isinstance(self.value, (str, int, float)) and ctx:
            return f'{alias_l}.{self.field.name} {self.comp_op} {ctx.placeholder(self.value)}'
        raise TypeError(f'Invalid Filter value type: {type(self.value).__name__}')

    def set_origin(self, origin: Select | Inner) -> None:
        if not isinstance(origin, (Select, Inner)):
            raise TypeError(f'Invalid Filter origin type: {type(origin).__name__}')
        object.__setattr__(self, 'origin', origin)


@dataclass(frozen=True, slots=True)
class Order:
    field: Field
    direction: Literal['ASC', 'DESC']
    origin: Select | Inner = field(default=None, init=False)

    def __post_init__(self):
        if not isinstance(self.field, Field):
            raise TypeError(f'Invalid Order field type: {type(self.field).__name__}')
        if self.direction not in ('ASC', 'DESC'):
            raise ValueError(f'Invalid Order direction: {self.direction}')
        
    def to_sql(self, alias: str) -> str:
        return f'{alias}.{self.field.name} {self.direction}'
        
    def set_origin(self, origin: Select | Inner) -> None:
        if not isinstance(origin, (Select, Inner)):
            raise TypeError(f'Invalid Order origin type: {type(origin).__name__}')
        object.__setattr__(self, 'origin', origin)
        

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
    
    def to_sql(self, alias: str):
        if type(self) is Field:
            return f'{alias}.{self.name}'
        raise Exception(f'Unhandled Field type: {type(self).__name__}')

@dataclass(frozen=True, slots=True)
class MaxField(Field):
    original: Field = field(init=False)

    def to_sql(self, alias):
        return f'MAX({alias}.{self.original.name}) AS {alias}.{self.name}'
    
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

    def to_sql(self, alias):
        return f'MIN({alias}.{self.original.name}) AS {alias}.{self.name}'
    
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
        self.ast_nodes.append(ASTNode('where', self))

        if self.join is None:
            for f in self.wheres:
                if f.field.table != self.calling_table:
                    raise Exception(f'field: {f.field.name}, is not from table: {self.calling_table}')
                f.set_origin(self)
        else:
            root_table = self.calling_table
            root_fields = self.fields
            join_table = self.join.inner_select.calling_table
            join_fields = self.join.inner_select.fields

            for f in self.wheres:
                if root_table != join_table:
                    if f.field.table == root_table:
                        f.set_origin(self)
                        continue
                    if f.field.table == join_table:
                        f.set_origin(self.join)
                        continue
                if root_table == join_table:
                    if f.field.is_in(root_fields):
                        f.set_origin(self)
                        continue
                    # unsure about this \/
                    if f.field.is_in(join_fields):
                        f.set_origin(self.join)
                        continue
                    # and this \/
                    if f.field.table == root_table:
                        f.set_origin(self)
                raise Exception(f'Cannot resolve filter origin for field: {f.field.name}')
        
        return self

    def group(self, field: Field) -> Select:
        self.group_by = (field)
        self.ast_nodes.append(ASTNode('group', self))

        if self.join is None:
            self.group_by = (field, 'left')
            return self
        else:
            root_table = self.calling_table
            root_fields = self.fields
            join_table = self.join.inner_select.calling_table
            join_fields = self.join.inner_select.fields

            if root_table != join_table:
                if field.table == root_table:
                    self.group_by = (field, 'left')
                    return self
                if field.table == join_table:
                    self.group_by = (field, 'right')
                    return self
            if root_table == join_table:
                if field.is_in(root_fields):
                    self.group_by = (field, 'left')
                    return self
                # unsure about this \/
                if field.is_in(join_fields):
                    self.group_by = (field, 'right')
                    return self
                # and this \/
                if field.table == root_table:
                    self.group_by = (field, 'left')
                    return self
            raise Exception(f'Cannot resolve origin for field in group by clause: {field.name}')

    
    def order(self, *orders: Order) -> Select:
        self.order_by = orders
        self.ast_nodes.append(ASTNode('order', self))

        if self.join is None:
            for o in self.order_by:
                if o.field.table != self.calling_table:
                    raise Exception(f'field: {o.field.name}, is not from table: {self.calling_table}')
                o.set_origin(self)
        else:
            root_table = self.calling_table
            root_fields = self.fields
            join_table = self.join.inner_select.calling_table
            join_fields = self.join.inner_select.fields

            for o in self.order_by:
                if root_table != join_table:
                    if o.field.table == root_table:
                        o.set_origin(self)
                        continue
                    if o.field.table == join_table:
                        o.set_origin(self.join)
                        continue
                if root_table == join_table:
                    if o.field.is_in(root_fields):
                        o.set_origin(self)
                        continue
                    # unsure about this \/
                    if o.field.is_in(join_fields):
                        o.set_origin(self.join)
                        continue
                    # and this \/
                    if o.field.table == root_table:
                        o.set_origin(self)
                raise Exception(f'Cannot resolve order origin for field: {o.field.name}')

        return self
    

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
    

def Query(root: Select) -> tuple[str, tuple[Any]]:
    ctx = SQLContext()
    ast_nodes = root.ast_nodes
    alias_mngr = root.alias_manager
    sql = ''

    for astn in ast_nodes:
        syntax = astn.syntax
        node = astn.node
        if isinstance(node, Inner):
            match syntax:
                case 'inner':
                    sql += 'INNER JOIN (\n'
                    continue
                case 'on':
                    alias_l = alias_mngr.get_alias(node.parent_select)
                    alias_r = alias_mngr.get_alias(node)
                    sql += f') {alias_r} ON '
                    for filter in node.ons:
                        sql += f'{filter.to_sql(alias_l, alias_r = alias_r)} AND '
                    sql = sql[0:-5] + '\n'
                    continue
                case _:
                    raise ValueError(f'Incorrect ASTNode syntax for Inner node: {syntax}')
        elif isinstance(node, Select):
            match syntax:
                case 'select':
                    sql += 'SELECT '

                    if len(node.fields) == 0:
                        sql += f'{alias_mngr.get_alias(node)}.*, '
                    else:
                        alias = alias_mngr.get_alias(node)
                        for field in node.fields:
                            sql += f'{field.to_sql(alias)}, '

                    if node.join and len(node.join.inner_select.fields) == 0:
                        sql += f'{alias_mngr.get_alias(node.join)}.*, '
                    elif node.join:
                        alias = alias_mngr.get_alias(node.join)
                        for field in node.join.inner_select.fields:
                            if not field.is_in(node.fields) and field.table != node.calling_table:
                                sql += f'{field.to_sql(alias)}, '

                    sql = sql.rstrip(', ') + f'\nFROM {node.calling_table.name} {alias_mngr.get_alias(node)}\n'
                    continue
                case 'where': # override and and or ?, also check max or minfields original for origin not self
                    sql += 'WHERE '
                    for filter in node.wheres:
                        alias = alias_mngr.get_alias(filter.origin)
                        sql += f'{filter.to_sql(alias, ctx = ctx)} AND '
                    sql = sql[0:-5] + '\n'
                    continue
                case 'group':
                    field, side = node.group_by
                    alias = ''
                    if side == 'left':
                        alias = alias_mngr.get_alias(node)
                    elif side == 'right':
                        alias = alias_mngr.get_alias(node.join)
                    sql += f'GROUP BY {alias}.{field.name}\n'
                    continue
                case 'order':
                    sql += 'ORDER BY '
                    for order in node.order_by:
                        alias = alias_mngr.get_alias(order.origin)
                        sql += f'{order.to_sql(alias)}, '
                    sql = sql.rstrip(', ') + '\n'
                    continue
                case _:
                    raise ValueError(f'Incorrect ASTNode syntax for Select node: {syntax}')
        else:
            raise TypeError(f'Invalid ASTNode node type: {type(node).__name__}')
    
    return sql.rstrip() + ';', tuple(ctx.params)