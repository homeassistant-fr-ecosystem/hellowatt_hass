# Project Overview: Hellowatt Home Assistant Integration

This document provides a concise overview of the Hellowatt Home Assistant Integration, a custom component for monitoring energy consumption data from HelloWatt.

## 1. Project Name and Domain

-   **Name**: Hellowatt Home Assistant Integration
-   **Home Assistant Domain**: `hellowatt`

## 2. Description and Purpose

The Hellowatt Home Assistant Integration is a custom component designed to connect Home Assistant with the HelloWatt energy monitoring service (French). Its primary purpose is to provide users with real-time access to their energy consumption data (electricity and gas), CO2 emissions, and cost breakdowns directly within Home Assistant.

## 3. Key Features

-   **Electricity Monitoring**: Daily, peak/off-peak, yesterday's, and weekly consumption, CO2 emissions, and detailed cost breakdowns (total, consumption, subscription).
-   **Gas Monitoring**: Daily, yesterday's, and weekly consumption, CO2 emissions, and detailed cost breakdowns (total, consumption, subscription).
-   **Additional Sensors**: Temperature monitoring.
-   **Historical Data Import**: Service to import historical consumption data into Home Assistant's long-term statistics.
-   **Multi-home/PDL Support**: Supports multiple Points de Livraison (PDLs) linked to a single HelloWatt account.
-   **Automatic Session Management**: Handles re-authentication with the HelloWatt API.
-   **Device Information**: Provides device details with contract information.
-   **Configuration via UI**: Easy setup through Home Assistant's integrations UI.

## 4. Technologies and Standards

-   **Platform**: Home Assistant Custom Component
-   **Language**: Python
-   **Integration Type**: `hub` (manages multiple entities from a single source)
-   **IoT Class**: `cloud_polling` (relies on polling a cloud service for data)
-   **API Communication**: Uses session-based authentication with CSRF tokens for communication with `https://www.hellowatt.fr/api`.
-   **Data Storage**: Utilizes Home Assistant's statistics database for historical data.

## 5. Installation and Configuration

### Installation Methods

-   **Manual Installation**: Copy the `custom_components/hellowatt` directory to your Home Assistant `custom_components` folder.
-   **HACS**: (Currently not available) Future support for installation via HACS (Home Assistant Community Store).

### Initial Setup

Configured via the Home Assistant UI:
1.  Navigate to Settings > Devices & Services.
2.  Click "Add Integration".
3.  Search for "HelloWatt".
4.  Enter HelloWatt account credentials (email and password).

The integration automatically discovers all associated homes (PDLs) and creates sensors.

## 6. Data Update Frequency

-   Data is polled from the HelloWatt API hourly.
-   Consumption data represents the previous day's usage (D-1) due to typical energy provider reporting delays.

## 7. Development and Contribution

-   **Codeowners**: `@homeassistant-fr-ecosystem`
-   **Documentation**: [GitHub Repository](https://github.com/homeassistant-fr-ecosystem/hellowatt_hass)
-   **Issue Tracker**: [GitHub Issues](https://github.com/homeassistant-fr-ecosystem/hellowatt_hass/issues)
-   **Key Design Patterns**: `CoordinatorEntity` for updates, `async/await` for API calls, robust session management, multi-PDL support, and integration with Home Assistant's external statistics.

## 8. Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by HelloWatt. Use at your own risk.
