### pypsql
*A structured query builder with fluent syntax for Pervasive SQL.*

> pypsql is a python package that provides a fluent, object-oriented API for defining and composing SQL
> queries against Pervasive SQL databases. It uses explicitly defined table and column structures to offer
> type-safety, autocompletion, and better query maintainability compared to raw SQL strings.


### Why?
- I am currently building an api interface into an old pervasive sql backend with `FastAPI` and `pyodbc`.
- Pervasive SQL is very limited compared to other flavors of SQL and this is not directly supported by python ORM's I've come accross.
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

def main():
    InventoryCosts = Table('InventoryCosts')
    TransDate = Field('TransDate', 'text', InventoryCosts)
    ItemRecNumber = Field('ItemRecNumber', 'number', InventoryCosts)
    Quantity = Field('Quantity', 'number', InventoryCosts)
    CostAcctRecNumber = Field('CostAcctRecNumber', 'number', InventoryCosts)
    RecordType = Field('RecordType', 'number', InventoryCosts)
    
    LineItem = Table('LineItem')
    ItemIsInactive = Field('ItemIsInactive', 'number', LineItem)
    ItemRecordNumber = Field('ItemRecordNumber', 'number', LineItem)
    StockingUM = Field('StockingUM', 'text', LineItem)
    ItemID = Field('ItemID', 'text', LineItem)

    sql = Query(
        LineItem
            .select(ItemID, StockingUM, ItemIsInactive)
            .inner(InventoryCosts
                .select(ItemRecNumber, TransDate, Quantity, CostAcctRecNumber, RecordType)
                .inner(InventoryCosts
                    .select(ItemRecNumber, RecordType, TransDate.MAX)
                    .where(RecordType.eq(50))
                    .group(ItemRecNumber)
                ).on(
                    ItemRecNumber.eq(ItemRecNumber),
                    TransDate.eq(TransDate.MAX),
                )
                .where(RecordType.eq(50))
            ).on(
                ItemRecordNumber.eq(ItemRecNumber),
            )
            .where(
                ItemIsInactive.eq(0),
                CostAcctRecNumber.eq(61),
            )
            .order(ItemRecNumber.ASC)
    )
    # The Query() function traverses the query structure
    # automatically handling table aliases and correctly referencing fields
    # in the WHERE and ON clauses.
    print(sql)
```
```
SELECT
lim1.ItemID, lim1.StockingUM, lim1.ItemIsInactive, irs4.ItemRecNumber, irs4.TransDate, irs4.Quantity, irs4.CostAcctRecNumber, irs4.RecordType
FROM
LineItem lim1
INNER JOIN (
SELECT
irs1.ItemRecNumber, irs1.TransDate, irs1.Quantity, irs1.CostAcctRecNumber, irs1.RecordType
FROM
InventoryCosts irs1
INNER JOIN (
SELECT
irs2.ItemRecNumber, irs2.RecordType, MAX(irs2.TransDate) AS irs2.MaxTransDate
FROM
InventoryCosts irs2
WHERE
irs2.RecordType = 50 
GROUP BY
irs2.ItemRecNumber
) irs3
ON
irs1.ItemRecNumber = irs3.ItemRecNumber AND irs1.TransDate = irs3.MaxTransDate 
WHERE
irs1.RecordType = 50 
) irs4
ON
lim1.ItemRecordNumber = irs4.ItemRecNumber 
WHERE
lim1.ItemIsInactive = 0 AND irs4.CostAcctRecNumber = 61 
ORDER BY
irs4.ItemRecNumber ASC;
```

> The below limitations are due to time constraints.
### Current Limitations
- Any fields referenced in WHERE or ON clauses must be included in the SELECT clause.
- Can only use = conditional.
- Can only chain condotions with AND. (handled automatically)