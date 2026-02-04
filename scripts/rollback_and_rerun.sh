#!/bin/bash
# rollback_and_rerun.sh - Support macro for rollback and re-run operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
DEFAULT_MODE="fifo"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Support macro for FIFO COGS rollback and re-run operations"
    echo ""
    echo "Options:"
    echo "  -t, --tenant-id TENANT     Tenant ID (required)"
    echo "  -r, --run-id RUN_ID        Run ID to rollback (required for rollback)"
    echo "  -s, --sales-file FILE      Sales CSV file path (required for re-run)"
    echo "  -l, --lots-file FILE       Lots CSV file path (optional)"
    echo "  -o, --operation OP         Operation: rollback, rerun, or both (default: both)"
    echo "  -d, --dry-run              Perform dry run validation only"
    echo "  -y, --yes                  Skip confirmation prompts"
    echo "  -v, --verbose              Verbose output"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Rollback and re-run with new data"
    echo "  $0 -t acme-corp -r RUN_123456 -s sales_corrected.csv"
    echo ""
    echo "  # Just rollback a run"
    echo "  $0 -t acme-corp -r RUN_123456 -o rollback"
    echo ""
    echo "  # Just run with new data (no rollback)"
    echo "  $0 -t acme-corp -s sales_new.csv -o rerun"
    echo ""
    echo "  # Dry run to validate data first"
    echo "  $0 -t acme-corp -s sales_new.csv -d"
}

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Parse command line arguments
TENANT_ID=""
RUN_ID=""
SALES_FILE=""
LOTS_FILE=""
OPERATION="both"
DRY_RUN=false
SKIP_CONFIRM=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        -r|--run-id)
            RUN_ID="$2"
            shift 2
            ;;
        -s|--sales-file)
            SALES_FILE="$2"
            shift 2
            ;;
        -l|--lots-file)
            LOTS_FILE="$2"
            shift 2
            ;;
        -o|--operation)
            OPERATION="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -y|--yes)
            SKIP_CONFIRM=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [ -z "$TENANT_ID" ]; then
    error "Tenant ID is required. Use -t or --tenant-id"
    exit 1
fi

if [ "$OPERATION" = "rollback" ] || [ "$OPERATION" = "both" ]; then
    if [ -z "$RUN_ID" ]; then
        error "Run ID is required for rollback operation. Use -r or --run-id"
        exit 1
    fi
fi

if [ "$OPERATION" = "rerun" ] || [ "$OPERATION" = "both" ]; then
    if [ -z "$SALES_FILE" ]; then
        error "Sales file is required for re-run operation. Use -s or --sales-file"
        exit 1
    fi
    
    if [ ! -f "$SALES_FILE" ]; then
        error "Sales file not found: $SALES_FILE"
        exit 1
    fi
fi

# Validate operation type
if [[ "$OPERATION" != "rollback" && "$OPERATION" != "rerun" && "$OPERATION" != "both" ]]; then
    error "Invalid operation: $OPERATION. Must be 'rollback', 'rerun', or 'both'"
    exit 1
fi

# Helper functions
check_api_health() {
    log "Checking API health..."
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health")
    
    if [ "$status_code" = "200" ]; then
        success "API is healthy"
        return 0
    else
        error "API health check failed (HTTP $status_code)"
        return 1
    fi
}

get_run_details() {
    local run_id=$1
    log "Fetching run details for $run_id..."
    
    local response=$(curl -s "$API_BASE_URL/api/v1/runs/$run_id")
    local status=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null)
    
    if [ "$status" = "null" ] || [ "$status" = "unknown" ]; then
        error "Failed to fetch run details or run not found"
        return 1
    fi
    
    echo "$response"
    return 0
}

perform_rollback() {
    local run_id=$1
    
    log "Getting current run status..."
    local run_details=$(get_run_details "$run_id")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    local current_status=$(echo "$run_details" | jq -r '.status')
    local tenant=$(echo "$run_details" | jq -r '.tenant_id')
    local created_at=$(echo "$run_details" | jq -r '.created_at')
    
    echo "📋 Run Details:"
    echo "   Run ID: $run_id"
    echo "   Tenant: $tenant"
    echo "   Status: $current_status"
    echo "   Created: $created_at"
    
    if [ "$current_status" = "rolled_back" ]; then
        warn "Run is already rolled back"
        return 0
    fi
    
    if [ "$current_status" != "completed" ]; then
        warn "Run status is '$current_status' - rollback may not work as expected"
    fi
    
    if [ "$SKIP_CONFIRM" != true ]; then
        echo ""
        read -p "❓ Are you sure you want to rollback run $run_id? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log "Rollback cancelled by user"
            return 1
        fi
    fi
    
    log "Performing rollback..."
    local rollback_response=$(curl -s -X POST "$API_BASE_URL/api/v1/runs/$run_id/rollback")
    local rollback_status=$(echo "$rollback_response" | jq -r '.status')
    
    if [ "$rollback_status" = "rolled_back" ] || [ "$rollback_status" = "already_rolled_back" ]; then
        success "Rollback completed successfully"
        return 0
    else
        error "Rollback failed: $rollback_response"
        return 1
    fi
}

perform_rerun() {
    local sales_file=$1
    local lots_file=$2
    
    log "Preparing re-run with sales file: $sales_file"
    if [ -n "$lots_file" ]; then
        log "Using lots file: $lots_file"
    fi
    
    # Upload sales file
    log "Uploading sales file..."
    local sales_upload_response=$(curl -s -X POST "$API_BASE_URL/api/v1/files/sales" \
        -F "tenant_id=$TENANT_ID" \
        -F "file=@$sales_file")
    
    local sales_upload_status=$(echo "$sales_upload_response" | jq -r '.status // "error"')
    if [ "$sales_upload_status" != "success" ]; then
        error "Sales file upload failed: $sales_upload_response"
        return 1
    fi
    
    success "Sales file uploaded successfully"
    
    # Upload lots file if provided
    if [ -n "$lots_file" ] && [ -f "$lots_file" ]; then
        log "Uploading lots file..."
        local lots_upload_response=$(curl -s -X POST "$API_BASE_URL/api/v1/files/lots" \
            -F "tenant_id=$TENANT_ID" \
            -F "file=@$lots_file")
        
        local lots_upload_status=$(echo "$lots_upload_response" | jq -r '.status // "error"')
        if [ "$lots_upload_status" != "success" ]; then
            error "Lots file upload failed: $lots_upload_response"
            return 1
        fi
        
        success "Lots file uploaded successfully"
    fi
    
    # Create run request
    local run_request="{
        \"tenant_id\": \"$TENANT_ID\",
        \"mode\": \"$DEFAULT_MODE\",
        \"sales_data\": [],
        \"lots_data\": []
    }"
    
    if [ "$DRY_RUN" = true ]; then
        log "🧪 This would be a dry run (validation only)"
        # Note: Add dry_run parameter to API if implemented
        warn "Dry run mode not yet implemented in API"
    fi
    
    if [ "$SKIP_CONFIRM" != true ] && [ "$DRY_RUN" != true ]; then
        echo ""
        read -p "❓ Ready to start new COGS calculation? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log "Re-run cancelled by user"
            return 1
        fi
    fi
    
    log "Starting new COGS calculation..."
    local run_response=$(curl -s -X POST "$API_BASE_URL/api/v1/runs" \
        -H "Content-Type: application/json" \
        -d "$run_request")
    
    local new_run_id=$(echo "$run_response" | jq -r '.run_id // "unknown"')
    local run_status=$(echo "$run_response" | jq -r '.status // "unknown"')
    
    if [ "$run_status" = "completed" ]; then
        success "New COGS calculation completed successfully"
        echo "📊 New Run ID: $new_run_id"
        
        # Show summary
        local total_cogs=$(echo "$run_response" | jq -r '.total_cogs // 0')
        local attribution_count=$(echo "$run_response" | jq -r '.attributions | length // 0')
        echo "💰 Total COGS: \$$total_cogs"
        echo "📋 Attribution entries: $attribution_count"
        
        return 0
    elif [ "$run_status" = "failed" ]; then
        error "New COGS calculation failed"
        local error_msg=$(echo "$run_response" | jq -r '.error_message // "Unknown error"')
        echo "Error details: $error_msg"
        return 1
    else
        error "Unexpected response from run creation: $run_response"
        return 1
    fi
}

# Main execution
main() {
    echo "🚀 FIFO COGS Rollback & Re-run Support Macro"
    echo "============================================="
    echo "Tenant: $TENANT_ID"
    echo "Operation: $OPERATION"
    if [ -n "$RUN_ID" ]; then
        echo "Run ID: $RUN_ID"
    fi
    if [ -n "$SALES_FILE" ]; then
        echo "Sales File: $SALES_FILE"
    fi
    if [ -n "$LOTS_FILE" ]; then
        echo "Lots File: $LOTS_FILE"
    fi
    echo ""
    
    # Check API health
    if ! check_api_health; then
        error "Cannot proceed - API is not available"
        exit 1
    fi
    
    # Perform operations based on selected mode
    case "$OPERATION" in
        "rollback")
            log "🔄 Performing rollback operation..."
            if perform_rollback "$RUN_ID"; then
                success "✅ Rollback operation completed successfully"
            else
                error "❌ Rollback operation failed"
                exit 1
            fi
            ;;
        "rerun")
            log "▶️  Performing re-run operation..."
            if perform_rerun "$SALES_FILE" "$LOTS_FILE"; then
                success "✅ Re-run operation completed successfully"
            else
                error "❌ Re-run operation failed"
                exit 1
            fi
            ;;
        "both")
            log "🔄 Performing rollback operation..."
            if perform_rollback "$RUN_ID"; then
                success "✅ Rollback completed"
                echo ""
                log "▶️  Performing re-run operation..."
                if perform_rerun "$SALES_FILE" "$LOTS_FILE"; then
                    success "✅ Complete rollback and re-run operation successful!"
                else
                    error "❌ Re-run failed after successful rollback"
                    exit 1
                fi
            else
                error "❌ Rollback failed - skipping re-run"
                exit 1
            fi
            ;;
    esac
    
    echo ""
    success "🎉 All operations completed successfully!"
}

# Run main function
main "$@"