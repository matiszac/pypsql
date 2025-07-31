### pypsql
*A structured query builder with fluent syntax for Pervasive SQL.*

> pypsql is a python package that ***should***(more on this under: Inspiration) provide a fluent, object-oriented API for defining and composing SQL
> queries against Pervasive SQL databases.
> It uses explicitly defined table and column structures to offer
> type-safety, autocompletion, and better query maintainability compared to raw SQL strings.

### Inspiration
- Prompted by a last minute attempt at the [Boot.dev July 2025 Hackathon](blog.boot.dev/news/hackathon-2025/). Spoiler alert, my first draft didn't make the cut.
- I wanted to make a simple query builder for a pyodbc/fastapi project I am working on.
- I wanted to attempt making query building simple and elegant which unfortunately meant I had to make assumptions about how certain queries or aggregate use should be resolved. This ultimately limits control but make making simple queries easy.

> I didn't realise how big of a scope this would be so it is unlikely that I could continue work on this after I implement most of the functionality of the SELECT statement along with more predecate types.


___
### Installation
```bash
# Clone repo
git clone https://github.com/matiszac/pypsql.git
```
```py
# Copy `pypsql` directory into your project and import these modules:
from pypsql import Table, Field, Query
```
___
### Limitations
- Data access only: SELECT, INNER JOIN
- GROUP BY only 1 column
- Comparison predicates only
- Predicate / Search Condition grouping in `ON` and `WHERE` by `AND` **only** *(automatic)*
- MIN and MAX aggregates only
- No column aliases, other than for MIN and MAX *(automatic)*
- No manual table or subquery aliases, they are automatically handled
___
### Features
- Automatic table / subquery aliasing with context management for columns *(each column knows what alias to use)*
- Simple aggregate syntax: `ColumnName.MAX`, `ColumnName.MIN`
- Simple ordering syntax: `Column.ASC`, `Column.DESC`
- Create comparison predicates using python syntax: `Column == 'name', Column2 != 0, Column3 < 4`
- Generated queries are parameterized: `sql, params = Query(...)`
___
### Example Usage
```py
from pypsql import Table, Field, Query2, Query

def main():
    # create table
    InventoryCosts = Table('InventoryCosts')
    # create fields (cloumns)
    TransDate = Field('TransDate', 'text', InventoryCosts)
    ItemRecNumber = Field('ItemRecNumber', 'int', InventoryCosts)
    Quantity = Field('Quantity', 'decimal', InventoryCosts)
    CostAcctRecNumber = Field('CostAcctRecNumber', 'int', InventoryCosts)
    RecordType = Field('RecordType', 'int', InventoryCosts)
    
    LineItem = Table('LineItem')
    ItemIsInactive = Field('ItemIsInactive', 'int', LineItem)
    ItemRecordNumber = Field('ItemRecordNumber', 'int', LineItem)
    StockingUM = Field('StockingUM', 'text', LineItem)
    ItemID = Field('ItemID', 'text', LineItem)

    sql, params = Query(
        LineItem
            .select(ItemID, StockingUM, ItemIsInactive)
            .inner(InventoryCosts
                .select(ItemRecNumber, TransDate, Quantity, CostAcctRecNumber, RecordType)
                .inner(InventoryCosts
                    .select(ItemRecNumber, RecordType, TransDate.MAX)
                    .where(RecordType == 50)
                    .group(ItemRecNumber)
                ).on(
                    ItemRecNumber == ItemRecNumber,
                    TransDate == TransDate.MAX,
                )
                .where(RecordType == 50)
            )
            .on(
                ItemRecordNumber == ItemRecNumber,
            )
            .where(
                ItemIsInactive == 0,
                CostAcctRecNumber == 61,
            )
            .order(ItemRecNumber.ASC)
    )

    print(sql)
    print(params)
```
```bash
# sql
SELECT lim1.ItemID, lim1.StockingUM, lim1.ItemIsInactive, irs1.ItemRecNumber, irs1.TransDate, irs1.Quantity, irs1.CostAcctRecNumber, irs1.RecordType
FROM LineItem lim1
INNER JOIN (
SELECT irs2.ItemRecNumber, irs2.TransDate, irs2.Quantity, irs2.CostAcctRecNumber, irs2.RecordType
FROM InventoryCosts irs2
INNER JOIN (
SELECT irs4.ItemRecNumber, irs4.RecordType, MAX(irs4.TransDate) AS irs4.MaxTransDate
FROM InventoryCosts irs4
WHERE irs4.RecordType = ?
GROUP BY irs4.ItemRecNumber
) irs3 ON irs2.ItemRecNumber = irs3.ItemRecNumber AND irs2.TransDate = irs3.MaxTransDate
WHERE irs2.RecordType = ?
) irs1 ON lim1.ItemRecordNumber = irs1.ItemRecNumber
WHERE lim1.ItemIsInactive = ? AND irs1.CostAcctRecNumber = ?
ORDER BY irs1.ItemRecNumber ASC;
# params
(50, 50, 0, 61)
```
___
### Other Examples
```py
TableName.select()
# > SELECT * FROM TableName tee1;
```
```py
Customers.select(Name, DateJoined, Address).where(Name == 'mike', DateJoined >= '2024-01-01').order(DateJoined.ASC)
# > SELECT cos1.Name, cos1.DateJoined, cos1.Address FROM Customers cos1 WHERE cos1.Name = ? AND cos1.DateJoined >= ? ORDER BY cos1.DateJoined ASC;
# > ('mike', '2024-01-01')
```
___
### References
[Actian Zen v15 SQL Engine Reference](https://docs.actian.com/zen/v15/index.html#page/sqlref/sqlintro.htm#ww83306)