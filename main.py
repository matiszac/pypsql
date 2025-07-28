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

    print(sql)





if __name__ == "__main__":
    main()
