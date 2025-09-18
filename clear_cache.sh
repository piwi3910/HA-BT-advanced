#!/bin/bash
# Script to clear Home Assistant cache and reload the integration

echo "Clearing Home Assistant translation cache..."

# Find and remove pycache directories
find /Volumes/DATA/git/HA-BT-advanced/custom_components -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Remove any .pyc files
find /Volumes/DATA/git/HA-BT-advanced/custom_components -name "*.pyc" -delete 2>/dev/null

echo "Cache cleared. Please:"
echo "1. Restart Home Assistant"
echo "2. Clear browser cache (Cmd+Shift+R on Mac, Ctrl+Shift+R on PC)"
echo "3. Reload the integration configuration page"