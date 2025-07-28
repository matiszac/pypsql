### pypsql
*A structured query builder with fluent syntax for Pervasive SQL.*

> pypsql is a python package that provides a fluent, object-oriented API for defining and composing SQL
> queries against Pervasive SQL databases. It uses explicitly defined table and column structures to offer
> type-safety, autocompletion, and better query maintainability compared to raw SQL strings.


### Why?
- I am currently building an api interface into an old pervasive sql backend with `FastAPI` and `pyodbc`.
- Pervasive SQL is very limited compared to other flavors of SQL and this is not directly supported by `SQLAcademy`.
- I just needed a simply library to model the database and easily build sql queries.

### What can it do?
- Currently not too much as this is a VERY early prototype developed within a few hours to make the `Boot.dev July 2025 Hackathon` submission deadline.

### Features
- Model Tables and Fields (limited).
  - Fields types: text, number.
- Automatic table aliasing.
- `SELECT`
  - Cherry pick columns.
- `INNER JOIN`
- `WHERE`
  - `=` Conditional
  - Conditional chaining by `AND`
- `GROUP BY`
- `ORDER BY`

### Installation
- `git clone https://github.com/matiszac/pypsql`
- Copy pypsql folder into project.
- OR `python3 main.py` to run demo.

### Example Usage
```py
from pypsql import Table, Field, Query

# define table
InventoryCosts = Table('InventoryCosts')
# define its fields
TransDate = Field('TransDate', 'text', InventoryCosts)
ItemRecNumber = Field('ItemRecNumber', 'number', InventoryCosts)
Quantity = Field('Quantity', 'number', InventoryCosts)
RecordType = Field('RecordType', 'number', InventoryCosts)

# define another table
LineItem = Table('LineItem')
# more fields
ItemIsInactive = Field('ItemIsInactive', 'number', LineItem)
ItemRecordNumber = Field('ItemRecordNumber', 'number', LineItem)

sql = Query(
  LineItem
    .select(ItemRecordNumber, ItemIsInactive)
    .inner(
      InventoryCosts
        .select(ItemRecNumber, TransDate, Quantity, RecordType)
        .where(RecordType.eq(50))
    ).on(
      ItemRecordNumber.eq(ItemRecNumber)
    )
    .where(ItemIsInactive.eq(0))
    .order(ItemRecordNumber.ASC)
)

# The Query() function traverses the query structure
# automatically handling table aliases and correctly referencing fields
# in the WHERE and ON clauses.
print(sql)
```
```
SELECT
lim2.ItemRecordNumber, lim2.ItemIsInactive, irs6.ItemRecNumber, irs6.TransDate, irs6.Quantity, irs6.RecordType
FROM
LineItem lim2
INNER JOIN (
SELECT
irs5.ItemRecNumber, irs5.TransDate, irs5.Quantity, irs5.RecordType
FROM
InventoryCosts irs5
WHERE
irs5.RecordType = 50 
) irs6
ON
lim2.ItemRecordNumber = irs6.ItemRecNumber 
WHERE
lim2.ItemIsInactive = 0 
ORDER BY
lim2.ItemRecordNumber ASC;
```

> The below limitations are due to time constraints.
### Current Limitations
- Any fields referenced in WHERE or ON clauses must be included in the SELECT clause.
- Can only use = conditional.
- Can only chain condotions with AND. (handled automatically)