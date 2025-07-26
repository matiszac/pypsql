SELECT
FROM
WHERE
ORDER

INNER JOIN
  TABLE NAME alias / (SELECT) alias
ON from.field = alias.field AND ...

Inner most joins should be processed first

Table provides select, which returns a select object
  select get 'from' from table, optional params are fields from table

Select provides where or inner join
  select provides


alias_stack = [
  'li',
  'ic',
  'ic1',
  'ic2',
  'ic3',
]

field_stack = [
  (ItemID, StockingUM, ItemIsInactive),
  (ItemRecNumber, CostAcctRecNumber, ...),
  (ItemRecNumber, CostAcctRecNumber, ...),
  (ItemRecNumber, TransDate.MAX),
  (ItemRecNumber, TransDate.MAX),
]

LineItem
  .select(ItemID, StockingUM, ItemIsInactive)
  .innerjoin(
    InventoryCosts
      .select(
        ItemRecNumber,
        CostAcctRecNumber,
        PostOrderNumber,
        TransDate,
        Quantity,
      )
      .innerjoin( # resolves back to select
        InventoryCosts
          .select(ItemRecNumber, TransDate.MAX) # ic3
          .where(RecordType.is(50)) # ic3
          .group(ItemRecNumber) # ic3
      )
      # ic2 -> ic3, ic2 -> ic3
      .on((ItemRecNumber, ItemRecNumber), (TransDate, TransDate))
      .where(RecordType.is(50)) # ic2
  )
    # ic -> ic1
  .on((ItemRecordNumber, ItemRecNumber))
  .where(ItemIsInactive.is(0), CostAcctRecNumber.is(61)) # li / ic
  .order(ItemRecNumber.ASC) # li / ic
