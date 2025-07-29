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

    # lim1 -> select
    # irs4 -> inner
    # irs1 -> select
    # irs3 -> inner
    # irs2 -> select
    # irs2 -> where
    # irs2 -> group
    # irs3 -> on
    # irs1 -> where
    # irs4 -> on
    # lim1 -> where
    # lim1 -> order

    select = (
        LineItem
            .select(ItemID, StockingUM, ItemIsInactive) # select node
            .inner(InventoryCosts # inner node
                .select(ItemRecNumber, TransDate, Quantity, CostAcctRecNumber, RecordType) # select node
                .inner(InventoryCosts # inner node
                    .select(ItemRecNumber, RecordType, TransDate.MAX) # select node
                    .where(RecordType == 50) # where node
                    .group(ItemRecNumber) # group node
                ).on( # on node
                    ItemRecNumber == ItemRecNumber,
                    TransDate == TransDate.MAX,
                )
                .where(RecordType == 50) # where node
            ) # inner results 
            .on( # on node
                ItemRecordNumber == ItemRecNumber,
            )
            .where( # where node
                # check self or inner join node if present
                ItemIsInactive == 0,
                CostAcctRecNumber == 61,
            )
            .order(ItemRecNumber.ASC) # order node
    )

    nodes = select.ast_nodes
    for node in nodes:
        print(f'{node.node.alias} -> {node.syntax}')

    #print(Query(select))





if __name__ == "__main__":
    main()
