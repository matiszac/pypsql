from __future__ import annotations
from typing import Literal


class Filter:
    def __init__(self, field: Field, comp_op, value):
        self.field = field
        self.comp_op = comp_op
        self.value = value


class Field:
    def __init__(self, name, type: Literal['number', 'text'], table: Table, is_max=False):
        self.table = table
        self.original = None
        self.name = name
        self.type = type
        self.is_max = is_max
        if not is_max:
            self.MAX = Field('Max'+self.name, self.type, self.table, is_max=True)
            self.MAX.original = self
        else:
            self.MAX = None
        self.ASC = (self, f'?.{self.name} ASC')
        self.DESC = (self, f'?.{self.name} DESC')

    def eq(self, value) -> Filter:
        return Filter(self, '=', value)

    def resolve(self, alias):
        if self.is_max:
            return f'MAX({alias}.{self.original.name}) AS {alias}.{self.name}'
        return f'{alias}.{self.name}'


class Table:
    def __init__(self, name):
        self.name = name
        self.ref_count = 0
    def select(self, *fields: Field):
        self.ref_count += 1
        return Select(self, *fields)


class Select:
    def __init__(self, calling_table: Table, *fields: Field):
        self.calling_table = calling_table
        n = calling_table.name.lower()
        # maybe hash and append refcount
        self.alias = f'{n[0]}{n[len(n)//2]}{n[-1]}{calling_table.ref_count}'
        self.fields = fields
        self.wheres = None
        self.group_by = None
        self.order_by = None
        self.join = None

    def inner(self, inner_select: Select) -> Inner:
        inner_select.calling_table.ref_count += 1
        self.join = Inner(self, inner_select)
        return self.join
    
    def where(self, *wheres: Filter) -> Select:
        self.wheres = wheres
        return self
    
    def group(self, field: Field) -> Select:
        self.group_by = field
        return self
    
    def order(self, *order_tups) -> Select:
        self.order_by = order_tups
        return self
    
    def resolve(self):
        query = 'SELECT '
        if len(self.fields) == 0:
            query += '* '
        else:
            for field in self.fields:
                query += field.resolve(self.alias) + ','
        return query[:-1] + f' FROM {self.calling_table.name} {self.alias}'


class Inner:
    def __init__(self, parent_select: Select, inner_select: Select):
        self.parent_select = parent_select
        self.inner_select = inner_select
        n = inner_select.calling_table.name.lower()
        i = inner_select.calling_table.ref_count
        self.alias = f'{n[0]}{n[len(n)//2]}{n[-1]}{i}'
        self.ons = []

    def on(self, *ons: Filter) -> Select:
        self.ons = ons
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
                    sel += field.resolve(part_v.alias) + ', '
                if part_v.join is not None and len(part_v.join.inner_select.fields) > 0:
                    for field in part_v.join.inner_select.fields:
                        if field in part_v.fields:
                            continue
                        if field.is_max and field.original in part_v.fields:
                            continue
                        sel += field.resolve(part_v.join.alias) + ', '
            sel = sel[0:-2] + f'\nFROM\n{part_v.calling_table.name} {part_v.alias}'
            if part_v.join is not None:
                if isinstance(part_v.join, Inner):
                    j = part_v.join
                    sel += f'\nINNER JOIN (\n?\n) {j.alias}\nON\n'
                    for on in j.ons:
                        if isinstance(on.value, Field):
                            sel += (
                                f'{part_v.alias}.{on.field.name}'
                                f' {on.comp_op} '
                                f'{j.alias}.{on.value.name}'
                                ' AND '
                            )
                    sel = sel[0:-4]
            if part_v.wheres is not None:
                sel += '\nWHERE\n'
                for filter in part_v.wheres:
                    alias = get_alias(filter.field, part_v, part_v.join)
                    sel += f'{alias}.{filter.field.name} {filter.comp_op} '
                    if filter.field.type == 'number':
                        sel += f'{filter.value} AND '
                    elif filter.field.type == 'text':
                        sel += f"'{filter.value}' AND "
                sel = sel[0:-4]
            if part_v.group_by is not None:
                sel += f'\nGROUP BY\n{part_v.alias}.{part_v.group_by.name}'
            if part_v.order_by is not None:
                sel += '\nORDER BY\n'
                for order in part_v.order_by:
                    alias = get_alias(order[0], part_v, part_v.join)
                    sel += f'{order[1].replace('?', alias)} AND '
                sel = sel[0:-5]
            if sql_parts:
                before = sql_parts.pop()
                sql_parts.append(sel.replace('?', before))
            else:
                sql_parts.append(sel)
    return sql_parts.pop()+';'


def get_alias(field: Field, select: Select, join: Inner):
    if join is None:
        return select.alias
    if field in select.fields:
        return select.alias
    if field in join.inner_select.fields:
        return join.alias
    

def get_parts(s: Select):
    r_stack = [{ 'select': s }]
    if s.join is None:
        return r_stack
    r_stack.append({ 'join': s.join })
    return r_stack + get_parts(s.join.inner_select)