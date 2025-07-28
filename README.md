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
```