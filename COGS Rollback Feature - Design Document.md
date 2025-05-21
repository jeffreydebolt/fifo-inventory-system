# COGS Rollback Feature - Design Document

## Overview

The COGS Rollback feature will allow users to undo COGS calculations if errors are discovered in the data or if purchase lots were missed. This provides a safety net for users, ensuring data integrity and allowing for corrections without manual intervention.

## Requirements

Based on user feedback, the COGS Rollback feature should:

1. Allow users to undo the most recent COGS calculation run
2. Maintain a transaction log of COGS calculations for audit purposes
3. Restore inventory to its pre-calculation state when rolled back
4. Provide clear feedback on the rollback process
5. Be implemented as a simple, reliable mechanism without complex version control

## Design Approach

We will implement the Transaction Log approach as specified by the user. This approach:
- Creates a record of each COGS calculation run
- Stores snapshots of inventory states before and after each run
- Provides a simple "Undo Last COGS Run" functionality

## Technical Design

### 1. Database Schema Extensions

We will add two new tables to the Supabase database:

#### `cogs_transaction_log` Table

```sql
CREATE TABLE cogs_transaction_log (
    transaction_id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sales_file_name TEXT,
    user_id TEXT,
    status TEXT DEFAULT 'completed',
    affected_skus INTEGER,
    total_quantity_sold INTEGER,
    total_cogs NUMERIC(15, 2)
);
```

#### `cogs_lot_changes` Table

```sql
CREATE TABLE cogs_lot_changes (
    change_id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    lot_id INTEGER NOT NULL REFERENCES purchase_lots(lot_id),
    sku TEXT NOT NULL,
    previous_remaining_qty INTEGER NOT NULL,
    new_remaining_qty INTEGER NOT NULL,
    quantity_change INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (run_id, lot_id)
);
```

### 2. FIFO Calculator Script Modifications

The FIFO calculator script will be enhanced to:

1. **Generate a unique Run ID** for each COGS calculation
2. **Record pre-processing inventory state** before making any changes
3. **Log all lot quantity changes** during processing
4. **Create a transaction summary** after processing

### 3. Rollback Implementation

A new script (`fifo_rollback.py`) will be created with the following functionality:

1. **List Recent Runs**: Display recent COGS calculation runs with summary information
2. **Rollback Last Run**: Restore inventory to its state before the most recent run
3. **Rollback Specific Run**: (Optional future enhancement) Allow rolling back to a specific point

### 4. Rollback Process Flow

The rollback process will:

1. Identify the most recent completed run in the transaction log
2. Retrieve all lot changes associated with that run
3. Reverse each change by updating the lot's remaining quantity to its previous value
4. Mark the transaction as "rolled back" in the transaction log
5. Generate a rollback report for the user

## User Interface

For the command-line script, we will add:

1. A new `--rollback` flag to the FIFO calculator script
2. A simple text-based menu for selecting rollback options
3. Clear console output showing the rollback progress and results

For the web dashboard (future enhancement):

1. A "Transaction History" section showing recent COGS calculations
2. An "Undo" button next to the most recent transaction
3. A confirmation dialog before performing rollback
4. Visual feedback during and after the rollback process

## Implementation Plan

### Phase 1: Core Rollback Functionality

1. Create the new database tables in Supabase
2. Modify the FIFO calculator to log transactions and changes
3. Implement the basic rollback script with "undo last run" functionality
4. Add comprehensive logging and error handling

### Phase 2: Web Dashboard Integration (Future)

1. Add transaction history view to the web dashboard
2. Implement rollback functionality in the web interface
3. Add visualization of affected inventory lots

## Considerations and Limitations

1. **Data Integrity**: The rollback process assumes no external changes to the affected lots between the original run and the rollback.
2. **Performance**: For very large datasets, the logging and rollback processes may impact performance.
3. **Concurrency**: The current design does not handle concurrent COGS calculations (assumed to be run sequentially).
4. **Partial Rollbacks**: The initial implementation will only support full run rollbacks, not partial or selective rollbacks.

## Next Steps

1. Implement the database schema extensions in Supabase
2. Modify the FIFO calculator script to support transaction logging
3. Develop the rollback script with command-line interface
4. Test the rollback functionality with various scenarios
5. Document the rollback process for users
