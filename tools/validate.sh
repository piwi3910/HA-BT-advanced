#!/bin/bash
set -e

echo "============================"
echo "Running Local Validation"
echo "============================"

# Attempt to run hassfest validation using Docker if available
if command -v docker &> /dev/null; then
  echo ""
  echo "============================"
  echo "Running hassfest validation"
  echo "============================"
  if docker pull ghcr.io/home-assistant/hassfest:latest; then
    # Create a temporary directory for validation
    TEMP_DIR=$(mktemp -d)
    mkdir -p "$TEMP_DIR/custom_components"

    # Copy only our custom integration for validation
    cp -r "custom_components/ha_bt_advanced" "$TEMP_DIR/custom_components/"

    # Run hassfest on just our integration
    docker run --rm -v "$TEMP_DIR://github/workspace" ghcr.io/home-assistant/hassfest
    HASSFEST_RESULT=$?

    # Clean up
    rm -rf "$TEMP_DIR"

    if [ $HASSFEST_RESULT -eq 0 ]; then
      echo "✓ Hassfest validation passed"
    else
      echo "✗ Hassfest validation failed with exit code $HASSFEST_RESULT"
    fi
  else
    echo "Couldn't pull hassfest Docker image - skipping hassfest validation"
  fi

  echo ""
  echo "============================"
  echo "Running HACS validation"
  echo "============================"
  if docker pull ghcr.io/hacs/action:main; then
    # Create a temporary directory for validation
    TEMP_DIR=$(mktemp -d)

    # Copy required files for HACS validation
    mkdir -p "$TEMP_DIR/custom_components"
    cp -r "custom_components/ha_bt_advanced" "$TEMP_DIR/custom_components/"
    cp -r ".github" "$TEMP_DIR/"
    cp "hacs.json" "$TEMP_DIR/"

    # Run HACS validation on the temporary directory
    docker run --rm -v "$TEMP_DIR://github/workspace" -e "GITHUB_WORKSPACE=/github/workspace" ghcr.io/hacs/action:main
    HACS_RESULT=$?

    # Clean up
    rm -rf "$TEMP_DIR"

    if [ $HACS_RESULT -eq 0 ]; then
      echo "✓ HACS validation passed"
    else
      echo "✗ HACS validation failed with exit code $HACS_RESULT"
    fi
  else
    echo "Couldn't pull HACS Docker image - skipping HACS validation"
  fi
fi

# Check manifest.json
echo "Checking manifest.json"
if [ -f "custom_components/ha_bt_advanced/manifest.json" ]; then
  echo "✓ manifest.json exists"
  
  if grep -q "\"iot_class\":" custom_components/ha_bt_advanced/manifest.json; then
    echo "✓ manifest.json contains iot_class"
  else
    echo "✗ manifest.json is missing iot_class"
  fi

  if grep -q "\"integration_type\":" custom_components/ha_bt_advanced/manifest.json; then
    echo "✓ manifest.json contains integration_type"
  else
    echo "✗ manifest.json is missing integration_type"
  fi

  if grep -q "\"version\":" custom_components/ha_bt_advanced/manifest.json; then
    echo "✓ manifest.json contains version"
  else
    echo "✗ manifest.json is missing version"
  fi

  if grep -q "\"dependencies\":" custom_components/ha_bt_advanced/manifest.json; then
    if grep -q "\"mqtt\"" custom_components/ha_bt_advanced/manifest.json; then
      echo "✓ manifest.json depends on mqtt"
    else
      echo "✗ manifest.json does not depend on mqtt"
    fi
    
    if grep -q "\"http\"" custom_components/ha_bt_advanced/manifest.json; then
      echo "✓ manifest.json depends on http"
    else
      echo "✗ manifest.json does not depend on http"
    fi
  else
    echo "✗ manifest.json is missing dependencies"
  fi
else
  echo "✗ manifest.json does not exist"
fi

# Check HACS.json files
echo ""
echo "Checking HACS.json files"
# Root folder
if [ -f "hacs.json" ]; then
  echo "✓ Root hacs.json exists"
  
  if grep -q "\"name\":" hacs.json; then
    echo "✓ Root hacs.json contains name"
  else
    echo "✗ Root hacs.json is missing name"
  fi
  
  if grep -q "\"homeassistant\":" hacs.json; then
    echo "✓ Root hacs.json contains homeassistant version"
  else
    echo "✗ Root hacs.json is missing homeassistant version"
  fi

  if grep -q "\"iot_class\":" hacs.json || grep -q "\"domains\":" hacs.json || grep -q "\"country\":" hacs.json; then
    echo "✗ Root hacs.json contains unauthorized fields (iot_class, domains, or country)"
  else
    echo "✓ Root hacs.json does not contain unauthorized fields"
  fi
else
  echo "✗ Root hacs.json does not exist"
fi

# .github folder
if [ -f ".github/HACS.json" ]; then
  echo "✓ .github/HACS.json exists"
  
  if grep -q "\"name\":" .github/HACS.json; then
    echo "✓ .github/HACS.json contains name"
  else
    echo "✗ .github/HACS.json is missing name"
  fi
  
  if grep -q "\"homeassistant\":" .github/HACS.json; then
    echo "✓ .github/HACS.json contains homeassistant version"
  else
    echo "✗ .github/HACS.json is missing homeassistant version"
  fi

  if grep -q "\"iot_class\":" .github/HACS.json || grep -q "\"domains\":" .github/HACS.json || grep -q "\"country\":" .github/HACS.json; then
    echo "✗ .github/HACS.json contains unauthorized fields (iot_class, domains, or country)"
  else
    echo "✓ .github/HACS.json does not contain unauthorized fields"
  fi
else
  echo "✗ .github/HACS.json does not exist"
fi

# Check services.yaml
echo ""
echo "Checking services.yaml step values"
if [ -f "custom_components/ha_bt_advanced/services.yaml" ]; then
  echo "✓ services.yaml exists"
  
  # Check for step values in latitude/longitude
  LATITUDE_STEP=$(grep -A10 "latitude:" custom_components/ha_bt_advanced/services.yaml | grep "step:" | head -n 1 | awk '{print $2}')
  LONGITUDE_STEP=$(grep -A10 "longitude:" custom_components/ha_bt_advanced/services.yaml | grep "step:" | head -n 1 | awk '{print $2}')
  
  echo "Latitude step value: $LATITUDE_STEP"
  echo "Longitude step value: $LONGITUDE_STEP"
  
  if [[ "$LATITUDE_STEP" == "0.000001" ]] && [[ "$LONGITUDE_STEP" == "0.000001" ]]; then
    echo "✓ Coordinates use precision-friendly step values (0.000001)"
  else
    echo "✗ Coordinates need step values of 0.000001"
  fi
else
  echo "✗ services.yaml does not exist"
fi

# Check translations
echo ""
echo "Checking translations"
if [ -f "custom_components/ha_bt_advanced/translations/en.json" ]; then
  echo "✓ English translations exist"
  
  # Check for state attributes format
  if grep -q '"state_attributes": {' custom_components/ha_bt_advanced/translations/en.json; then
    echo "✓ Translations use proper dictionary format for state attributes"
  else
    echo "✗ Translations may have improperly formatted state attributes"
  fi
else
  echo "✗ English translations do not exist"
fi

echo ""
echo "Validation complete!"