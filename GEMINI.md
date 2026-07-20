# Project Rules: Helllowatt Home Assistant Integration

## 1. Project Context
This integration connects Home Assistant with the HelloWatt energy monitoring service, providing real-time access to energy consumption data (electricity/gas), CO2 emissions, and cost breakdowns.

## 2. Standards
- Refer to `/.gemini/rules/shared_python.md` for all development, testing, linting, and type-checking standards.

## 3. Project-Specific Notes
- **Domain**: `hellowatt`
- **Integration Type**: `hub` (`cloud_polling`)
- **API**: Uses `https://www.hellowatt.fr/api` with session-based authentication.
