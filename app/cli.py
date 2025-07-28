#!/usr/bin/env python3
"""
CLI interface for FIFO COGS system.
"""
import click
import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import PurchaseLot, Sale
from core.fifo_engine import FIFOEngine
from services.journaled_calculator import JournaledCalculator
from tests.unit.csv_normalizer import CSVNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@click.group()
def cli():
    """FIFO COGS Calculator CLI"""
    pass


@cli.command()
@click.option('--tenant-id', required=True, help='Tenant ID')
@click.option('--sales-file', required=True, type=click.Path(exists=True), help='Sales CSV file')
@click.option('--lots-file', type=click.Path(exists=True), help='Lots CSV file (optional)')
@click.option('--mode', default='fifo', type=click.Choice(['fifo', 'avg']), help='Calculation mode')
@click.option('--start-month', help='Start month YYYY-MM')
@click.option('--output-dir', default='output', help='Output directory')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def run(tenant_id, sales_file, lots_file, mode, start_month, output_dir, dry_run):
    """
    Execute a COGS calculation run.
    
    Example:
        python -m app.cli run --tenant-id tenant-a --sales-file golden/golden_sales_clean.csv
    """
    try:
        click.echo(f"🚀 Starting COGS calculation run for tenant: {tenant_id}")
        
        if dry_run:
            click.echo("🔍 DRY RUN MODE - No changes will be made")
        
        # Load sales data
        click.echo(f"📊 Loading sales data from: {sales_file}")
        sales = load_sales_from_csv(sales_file)
        click.echo(f"   Loaded {len(sales)} sales transactions")
        
        # Load or create sample lots data
        if lots_file:
            click.echo(f"📦 Loading lots data from: {lots_file}")
            lots = load_lots_from_csv(lots_file)
        else:
            click.echo("📦 Creating sample lots data (no lots file provided)")
            lots = create_sample_lots_for_sales(sales, tenant_id)
        
        click.echo(f"   Loaded {len(lots)} purchase lots")
        
        if dry_run:
            click.echo("\n🔍 DRY RUN SUMMARY:")
            click.echo(f"   - Tenant: {tenant_id}")
            click.echo(f"   - Sales: {len(sales)} transactions")
            click.echo(f"   - Lots: {len(lots)} purchase lots")
            click.echo(f"   - Mode: {mode}")
            click.echo(f"   - Output: {output_dir}")
            return
        
        # Initialize calculator
        engine = FIFOEngine()
        calculator = JournaledCalculator(engine)
        
        # Execute run
        click.echo(f"⚙️  Executing {mode.upper()} calculation...")
        result = calculator.create_and_execute_run(
            tenant_id=tenant_id,
            lots=lots,
            sales=sales,
            mode=mode,
            start_month=start_month,
            created_by="CLI"
        )
        
        run_id = result['run_id']
        click.echo(f"✅ Run completed successfully!")
        click.echo(f"   Run ID: {run_id}")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Total COGS: ${result['total_cogs']}")
        click.echo(f"   Sales Processed: {len(result['attributions'])}")
        click.echo(f"   Validation Errors: {len(result['validation_errors'])}")
        
        # Save outputs
        os.makedirs(output_dir, exist_ok=True)
        save_run_outputs(result, output_dir, run_id)
        
        click.echo(f"📁 Outputs saved to: {output_dir}")
        click.echo(f"   - Run summary: {output_dir}/run_{run_id}_summary.txt")
        click.echo(f"   - COGS attributions: {output_dir}/run_{run_id}_attributions.csv")
        click.echo(f"   - Monthly summaries: {output_dir}/run_{run_id}_summaries.csv")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('run_id')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def rollback(run_id, confirm):
    """
    Rollback a COGS calculation run.
    
    Example:
        python -m app.cli rollback run_123 --confirm
    """
    try:
        if not confirm:
            click.confirm(f"Are you sure you want to rollback run {run_id}?", abort=True)
        
        click.echo(f"🔄 Rolling back run: {run_id}")
        
        # Initialize calculator
        engine = FIFOEngine()
        calculator = JournaledCalculator(engine)
        
        # Execute rollback
        result = calculator.rollback_run(run_id, rollback_by="CLI")
        
        click.echo(f"✅ Rollback completed!")
        click.echo(f"   Run ID: {result['run_id']}")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Message: {result['message']}")
        
        if result.get('rollback_run_id'):
            click.echo(f"   Rollback Run ID: {result['rollback_run_id']}")
        
        if result.get('restored_lots_count'):
            click.echo(f"   Restored Lots: {result['restored_lots_count']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--tenant-id', help='Filter by tenant ID')
@click.option('--status', help='Filter by status')
@click.option('--limit', default=20, help='Number of runs to show')
def list_runs(tenant_id, status, limit):
    """
    List COGS calculation runs.
    
    Example:
        python -m app.cli list-runs --tenant-id tenant-a --status completed
    """
    try:
        click.echo("📋 COGS Calculation Runs")
        click.echo("=" * 50)
        
        # In real implementation, would query database
        click.echo("No runs found (database not connected in CLI mode)")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('run_id')
@click.option('--format', default='csv', type=click.Choice(['csv', 'json', 'text']), 
              help='Output format')
@click.option('--output-file', help='Save to file instead of stdout')
def journal_entry(run_id, format, output_file):
    """
    Generate journal entry for accounting systems.
    
    Example:
        python -m app.cli journal-entry run_123 --format csv --output-file je.csv
    """
    try:
        click.echo(f"📊 Generating journal entry for run: {run_id}")
        
        # Initialize calculator
        engine = FIFOEngine()
        calculator = JournaledCalculator(engine)
        
        # Generate journal entry
        content = calculator.generate_journal_entry(run_id, format)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(content)
            click.echo(f"✅ Journal entry saved to: {output_file}")
        else:
            click.echo(f"📄 Journal Entry ({format.upper()}):")
            click.echo("-" * 40)
            click.echo(content)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def load_sales_from_csv(csv_path: str) -> list:
    """Load sales from CSV file"""
    df = pd.read_csv(csv_path)
    normalizer = CSVNormalizer()
    
    normalized_df = normalizer.normalize_sales_csv(df)
    sale_dicts = normalizer.create_sale_objects(normalized_df)
    
    sales = []
    for sale_dict in sale_dicts:
        sale = Sale(**sale_dict)
        sales.append(sale)
    
    return sales


def load_lots_from_csv(csv_path: str) -> list:
    """Load lots from CSV file"""
    # Implementation would depend on lots CSV format
    return []


def create_sample_lots_for_sales(sales: list, tenant_id: str) -> list:
    """Create sample lots with enough inventory for the sales"""
    # Group sales by SKU to determine needed inventory
    sku_totals = {}
    for sale in sales:
        sku_totals[sale.sku] = sku_totals.get(sale.sku, 0) + sale.quantity_sold
    
    lots = []
    for sku, total_needed in sku_totals.items():
        # Create a lot with 150% of needed quantity
        lot = PurchaseLot(
            lot_id=f"LOT_{sku}_001",
            sku=sku,
            received_date=datetime(2024, 1, 1),
            original_quantity=int(total_needed * 1.5),
            remaining_quantity=int(total_needed * 1.5),
            unit_price=Decimal("10.00"),
            freight_cost_per_unit=Decimal("1.00"),
            tenant_id=tenant_id
        )
        lots.append(lot)
    
    return lots


def save_run_outputs(result: dict, output_dir: str, run_id: str):
    """Save run outputs to files"""
    # Save summary
    with open(f"{output_dir}/run_{run_id}_summary.txt", 'w') as f:
        f.write(f"COGS Calculation Run Summary\n")
        f.write(f"Run ID: {run_id}\n")
        f.write(f"Status: {result['status']}\n")
        f.write(f"Total COGS: ${result['total_cogs']}\n")
        f.write(f"Sales Processed: {len(result['attributions'])}\n")
        f.write(f"Validation Errors: {len(result['validation_errors'])}\n")
    
    # Save attributions
    if result['attributions']:
        attributions_data = []
        for attr in result['attributions']:
            attributions_data.append({
                'sale_id': attr.sale_id,
                'sku': attr.sku,
                'sale_date': attr.sale_date,
                'quantity_sold': attr.quantity_sold,
                'total_cogs': float(attr.total_cogs),
                'average_unit_cost': float(attr.average_unit_cost)
            })
        
        df = pd.DataFrame(attributions_data)
        df.to_csv(f"{output_dir}/run_{run_id}_attributions.csv", index=False)
    
    # Save summaries
    if result['summaries']:
        summaries_data = []
        for summary in result['summaries']:
            summaries_data.append({
                'sku': summary.sku,
                'period': summary.period,
                'total_quantity_sold': summary.total_quantity_sold,
                'total_cogs': float(summary.total_cogs),
                'average_unit_cost': float(summary.average_unit_cost)
            })
        
        df = pd.DataFrame(summaries_data)
        df.to_csv(f"{output_dir}/run_{run_id}_summaries.csv", index=False)


if __name__ == '__main__':
    cli()