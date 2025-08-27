# PRODUCTION SAFETY CHECKLIST

## BEFORE MAKING ANY CHANGES

### 1. Backup Verification
- [ ] Production FIFO calculator backed up: `fifo_calculator_supabase_PRODUCTION_BACKUP_*.py`
- [ ] Dashboard application backed up: `cogs-dashboard_PRODUCTION_BACKUP_*`  
- [ ] Output directories archived: `fifo_production_outputs_backup_*.tar.gz`
- [ ] Database state documented (run query below)

```sql
SELECT 
  COUNT(*) as total_lots,
  SUM(remaining_unit_qty) as total_inventory,
  COUNT(DISTINCT sku) as unique_skus,
  MAX(received_date) as latest_lot_date
FROM purchase_lots 
WHERE remaining_unit_qty > 0;
```

### 2. Environment Setup
- [ ] Test environment configured (`.env.test`)
- [ ] Production environment variables unchanged
- [ ] Test tenant ID different from production
- [ ] API running on different port (8001) for testing

### 3. Functional Verification
- [ ] Current dashboard loads without errors
- [ ] User can authenticate successfully  
- [ ] Recent COGS runs visible in interface
- [ ] FIFO calculator runs without errors on sample data

### 4. Client Protection
- [ ] No changes to `purchase_lots` table structure
- [ ] No modifications to existing FIFO calculation logic
- [ ] All changes use feature flags or separate endpoints
- [ ] Rollback procedures tested and documented

## DURING DEVELOPMENT

### Change Process
1. Work in test environment only
2. Use test tenant ID for all operations
3. Test with sample data before touching real data
4. Document every change made
5. Create rollback script for each modification

### Testing Requirements
- [ ] Unit tests pass for new functionality
- [ ] Integration tests verify existing functionality unchanged
- [ ] FIFO calculations produce identical results to production
- [ ] Dashboard remains fully functional
- [ ] All API endpoints respond correctly

## BEFORE DEPLOYMENT

### Validation Checklist
- [ ] All tests pass
- [ ] Production backup is recent (within 24 hours)
- [ ] Rollback script tested and ready
- [ ] Client notification plan prepared (if any downtime)
- [ ] Monitoring systems ready to detect issues

### Deployment Safety
- [ ] Deploy during low-usage hours
- [ ] Monitor system health immediately after deployment
- [ ] Verify client can access system within 1 hour
- [ ] Confirm FIFO calculations produce expected results

## EMERGENCY PROCEDURES

### If Something Breaks
1. **STOP ALL CHANGES IMMEDIATELY**
2. **Restore from backup**:
   ```bash
   # Restore FIFO calculator
   cp fifo_calculator_supabase_PRODUCTION_BACKUP_*.py fifo_calculator_supabase.py
   
   # Restore dashboard
   rm -rf cogs-dashboard
   mv cogs-dashboard_PRODUCTION_BACKUP_* cogs-dashboard
   ```
3. **Test restoration**
4. **Document what went wrong**
5. **Notify client if necessary**

### Contact Information
- **Client Impact**: Critical - affects daily operations
- **Response Time Required**: Within 1 hour
- **Escalation**: Restore from backup first, investigate later

## SUCCESS CRITERIA

System is healthy when:
- [ ] Client can log in and access dashboard
- [ ] FIFO calculations produce accurate results
- [ ] Inventory levels update correctly with sales
- [ ] Historical data remains intact and accessible
- [ ] CSV reports generate successfully
- [ ] No error messages in application logs

## NOTES
- This is a LIVE PRODUCTION SYSTEM with active client data
- Every change must be reversible
- Quality and safety are more important than speed
- When in doubt, don't make the change