from pypsql import Table, Field, Query

def main():
    InventoryCosts = Table('InventoryCosts')
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


if __name__ == "__main__":
    main()
