def main():
    TransDate = Field('TransDate')
    ItemRecNumber = Field('ItemRecNumber')
    InventoryCosts = Table('InventoryCosts')

    query = InventoryCosts.select(ItemRecNumber, TransDate.MAX).resolve()
    print(query)


class Field:
    def __init__(self, name, is_max=False):
        self.original = None
        self.name = name
        self.is_max = is_max
        if not is_max:
            self.MAX = Field('Max'+self.name, is_max=True)
            self.MAX.original = self.name
        else:
            self.MAX = None

    def resolve(self, alias):
        if self.is_max:
            return f'MAX({alias}.{self.original}) AS {alias}.{self.name}'
        return f'{alias}.{self.name}'


class Table:
    def __init__(self, name):
        self.name = name

    def select(self, *fields: Field):
        return Select(self, *fields)


class Select:
    def __init__(self, calling_table, *fields: Field):
        self.calling_table = calling_table
        self.alias = calling_table.name[0:2] + '_a'
        self.fields = fields

    def resolve(self):
        query = 'SELECT '
        if len(self.fields) == 0:
            query += '* '
        else:
            for field in self.fields:
                query += field.resolve(self.alias) + ', '
        return query[:-2] + f' FROM {self.calling_table.name} {self.alias}'






if __name__ == "__main__":
    main()
