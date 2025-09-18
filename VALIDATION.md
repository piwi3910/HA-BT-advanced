# HA-BT-Advanced Validation

This document outlines the validation requirements for the HA-BT-Advanced integration and how to test them locally.

## Local Validation

We've created a validation script that checks for common HACS and Home Assistant integration requirements:

```bash
./tools/validate.sh
```

This script performs several types of validation:

### Basic Validation
Checks for:
- manifest.json requirements
- HACS.json requirements in both root and .github directories
- services.yaml step values for coordinates
- translations format

### Docker-based Validation
If Docker is available, the script will also run:

1. **hassfest validation**
   - Uses the same Docker container as GitHub Actions
   - Performs comprehensive validation of integration requirements
   - Checks manifest formatting, services, and more

2. **HACS validation**
   - Uses the HACS validation container
   - Validates HACS-specific requirements
   - Ensures the integration will be compatible with HACS

## Fixed Issues

The following issues have been fixed:

1. **HACS.json in root directory**
   - Removed unauthorized fields: iot_class, domains, country
   - Kept only allowed fields: name, render_readme, homeassistant

2. **Created .github/HACS.json**
   - This file is required by HACS validation
   - Includes only allowed fields: name, render_readme, homeassistant

3. **Updated services.yaml**
   - Fixed precision of step values for latitude/longitude selectors
   - Set step value to 0.000001 for precise coordinate input

4. **Fixed translations format**
   - Ensured state_attributes uses the proper dictionary format

## GitHub Repository Requirements

For the GitHub repository to pass HACS validation, you must complete these steps (these cannot be done through code changes alone):

1. **Add Repository Description:** (Required)
   - Go to your GitHub repository page
   - Click the "Settings" tab
   - Add a descriptive summary in the "Description" field
   - Example: "BLE iBeacon Triangulation with ESPHome Proxies for Home Assistant"

2. **Add Repository Topics:** (Required)
   - Still in the Settings tab of your repository
   - Find the "Topics" section
   - Add relevant topics (at least 8 recommended):
     - home-assistant
     - homeassistant
     - hacs
     - custom-integration
     - bluetooth
     - ble
     - triangulation
     - esphome
     - ibeacon
     - location-tracking

3. **Add to Home Assistant Brands Repository:** (Optional)
   - This gives your integration an official icon in Home Assistant
   - Submit a pull request to: https://github.com/home-assistant/brands
   - Follow the guidelines at: https://developers.home-assistant.io/docs/creating_integration_manifest#logo
   - Note: This is optional but recommended for a professional appearance

3. **Add GitHub Workflow:**
   - We've created the necessary .github/workflows directory
   - Consider adding CI/CD pipelines for automated testing

## Running Validation During Development

To avoid the need to push to GitHub for validation, use:

```bash
./tools/validate.sh
```

This script will help catch common issues before pushing to GitHub.