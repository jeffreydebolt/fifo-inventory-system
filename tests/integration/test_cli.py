"""
Integration tests for CLI commands.
Tests all CLI functionality for local usage.
"""
import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.cli import cli


class TestCLICommands(unittest.TestCase):
    """Test CLI commands for local usage"""
    
    def setUp(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test sales file
        self.test_sales_file = os.path.join(self.temp_dir, "test_sales.csv")
        with open(self.test_sales_file, 'w') as f:
            f.write("sku,units moved,Month\n")
            f.write("SKU-A,30,June 2024\n")
            f.write("SKU-B,20,June 2024\n")
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_run_command_dry_run(self):
        """Test: python -m app.cli run with --dry-run"""
        result = self.runner.invoke(cli, [
            'run',
            '--tenant-id', 'test-tenant',
            '--sales-file', self.test_sales_file,
            '--dry-run'
        ])
        
        # Should succeed in dry run mode
        self.assertEqual(result.exit_code, 0)
        self.assertIn("DRY RUN MODE", result.output)
        self.assertIn("test-tenant", result.output)
        self.assertIn("2 transactions", result.output)
    
    def test_cli_run_command_help(self):
        """Test: python -m app.cli run --help"""
        result = self.runner.invoke(cli, ['run', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Execute a COGS calculation run", result.output)
        self.assertIn("--tenant-id", result.output)
        self.assertIn("--sales-file", result.output)
    
    def test_cli_rollback_command_help(self):
        """Test: python -m app.cli rollback --help"""
        result = self.runner.invoke(cli, ['rollback', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Rollback a COGS calculation run", result.output)
        self.assertIn("RUN_ID", result.output)
    
    def test_cli_list_runs_command(self):
        """Test: python -m app.cli list-runs"""
        result = self.runner.invoke(cli, ['list-runs'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("COGS Calculation Runs", result.output)
    
    def test_cli_journal_entry_command_help(self):
        """Test: python -m app.cli journal-entry --help"""
        result = self.runner.invoke(cli, ['journal-entry', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Generate journal entry", result.output)
        self.assertIn("--format", result.output)
    
    def test_cli_run_command_missing_tenant_id(self):
        """Test: CLI run command fails without tenant-id"""
        result = self.runner.invoke(cli, [
            'run',
            '--sales-file', self.test_sales_file
        ])
        
        # Should fail due to missing required option
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("tenant-id", result.output.lower())
    
    def test_cli_run_command_missing_sales_file(self):
        """Test: CLI run command fails without sales-file"""
        result = self.runner.invoke(cli, [
            'run',
            '--tenant-id', 'test-tenant'
        ])
        
        # Should fail due to missing required option
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("sales-file", result.output.lower())
    
    def test_cli_run_command_nonexistent_sales_file(self):
        """Test: CLI run command fails with nonexistent sales file"""
        result = self.runner.invoke(cli, [
            'run',
            '--tenant-id', 'test-tenant',
            '--sales-file', '/nonexistent/file.csv'
        ])
        
        # Should fail due to file not existing
        self.assertNotEqual(result.exit_code, 0)
    
    def test_cli_rollback_without_confirmation(self):
        """Test: CLI rollback requires confirmation"""
        result = self.runner.invoke(cli, [
            'rollback',
            'test-run-id'
        ], input='n\n')  # Answer 'no' to confirmation
        
        # Should abort due to no confirmation
        self.assertNotEqual(result.exit_code, 0)
        # CLI shows error when aborted
        self.assertIn("Error", result.output)
    
    def test_cli_main_help(self):
        """Test: Main CLI help"""
        result = self.runner.invoke(cli, ['--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn("FIFO COGS Calculator CLI", result.output)
        self.assertIn("run", result.output)
        self.assertIn("rollback", result.output)
        self.assertIn("list-runs", result.output)
        self.assertIn("journal-entry", result.output)


if __name__ == '__main__':
    unittest.main()