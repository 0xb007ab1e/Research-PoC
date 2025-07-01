#!/bin/bash

# sbom-podman.sh - A script to handle SBOM generation using syft for Podman
#
# Usage:
#   sbom-podman.sh -t <image:tag> [-f <spdx,cyclonedx>] [-o <outdir>] -- [podman build options]
#
# Options:
#   -t    Specify the image and tag (e.g., image:tag)
#   -f    Specify the format(s) for SBOM (spdx, cyclonedx) [optional]
#   -o    Specify the output directory [optional]
#
# Global Configuration:
#   The script reads SBOM_FORMATS and SBOM_OUT_DIR environment variables
#   (typically set by including scripts/sbom.conf.mk in your Makefile)
#   and falls back to built-in defaults if not set.

# Set default values (fallback if environment variables are not set)
DEFAULT_FORMATS="spdx,cyclonedx"
DEFAULT_OUT_DIR="sbom-reports"

# Parse command line arguments
while getopts ":t:f:o:" opt; do
  case $opt in
    t) IMAGE_TAG="$OPTARG"
    ;;
    f) FORMATS="$OPTARG"
    ;;
    o) OUTDIR="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1
    ;;
  esac
  shift $((OPTIND -1))
done

# Detect container engine
if command -v docker &> /dev/null
then
    echo "Using Docker, exiting."
    exit 0
fi

if ! command -v podman &> /dev/null
then
    echo "Podman not installed, exiting."
    exit 1
fi

# Build with Podman
podman build "$@"
BUILD_EXIT_CODE=$?

if [ $BUILD_EXIT_CODE -ne 0 ]; then
  exit $BUILD_EXIT_CODE
fi

# Split formats and generate SBOM
IFS=',' read -ra ADDR <<< "$FORMATS"
for format in "${ADDR[@]}"; do
  case $format in
    spdx)
      syft "$IMAGE_TAG" -o spdx-json="$OUTDIR/sbom-${IMAGE_TAG//:/-}.spdx.json"
    ;;
    cyclonedx)
      syft "$IMAGE_TAG" -o cyclonedx-json="$OUTDIR/sbom-${IMAGE_TAG//:/-}.cyclonedx.json"
    ;;
    *)
      echo "Unsupported format: $format"
      exit 1
    ;;
  esac
done

exit $BUILD_EXIT_CODE

