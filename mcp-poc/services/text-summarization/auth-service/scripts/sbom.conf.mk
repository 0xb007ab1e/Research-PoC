# SBOM Configuration Makefile snippet
# Include this in your Makefile with: include scripts/sbom.conf.mk
#
# This file defines global variables for SBOM generation that can be
# overridden by environment variables or make command line arguments.

# Default SBOM formats (comma-separated)
# Supported formats: spdx, cyclonedx
SBOM_FORMATS ?= spdx,cyclonedx

# Default output directory for SBOM reports
SBOM_OUT_DIR ?= sbom-reports

# Export variables so they can be used by shell scripts
export SBOM_FORMATS
export SBOM_OUT_DIR

.PHONY: sbom-config-info

# Display current SBOM configuration
sbom-config-info:
	@echo "SBOM Configuration:"
	@echo "  Formats: $(SBOM_FORMATS)"
	@echo "  Output Directory: $(SBOM_OUT_DIR)"
