# Ford Firmware Engineering Tool - Backend API

ASP.NET Core 8.0 backend API for processing Ford instrument cluster (IPC) firmware with custom bootsplash logos, including firmware analysis capabilities via binwalk and dumpIFS ports.

## Overview

This backend service provides comprehensive firmware processing capabilities:

### Firmware Modification
1. **Parses VBF files** - Extracts header metadata and data blocks
2. **Extracts TAR archives** - Unpacks firmware container archives
3. **Processes bitmaps.bin** - Handles Ford's bitmap container format
4. **Unpacks KZB archives** - Extracts Kanzi Studio archive format
5. **Modifies spritesheets** - Applies custom logos to animation frames
6. **Rebuilds everything** - Repacks all archives into valid VBF format

### Firmware Analysis (NEW)
- **Binwalk Integration** - Signature scanning, entropy analysis, file extraction
- **DumpIFS Integration** - QNX IFS filesystem parsing and extraction
- **Hash Calculation** - MD5, SHA1, SHA256 checksums
- **Entropy Analysis** - Detect compressed/encrypted regions

## Prerequisites

- .NET 8.0 SDK
- Docker (optional, for containerized deployment)
- Azure subscription (for cloud deployment)

## Quick Start

### Local Development

```bash
# Restore dependencies
dotnet restore

# Run the application
dotnet run

# API will be available at https://localhost:5001
# Swagger UI at https://localhost:5001/swagger
```

### Docker Deployment

```bash
docker build -t ford-firmware-api .
docker run -p 8080:8080 ford-firmware-api
```

## API Endpoints

### IPC Logo Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ipc-logo` | POST | Process firmware with custom logo (returns VBF) |
| `/api/ipc-logo/detailed` | POST | Process with detailed JSON response |

### Firmware Analysis (Binwalk)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Comprehensive firmware analysis |
| `/api/binwalk/scan` | POST | Scan for file signatures |
| `/api/binwalk/entropy` | POST | Entropy analysis |
| `/api/binwalk/extract` | POST | Extract embedded files |
| `/api/binwalk/hash` | POST | Calculate file hashes |

### QNX IFS Processing (DumpIFS)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dumpifs` | POST | Parse QNX IFS image |
| `/api/dumpifs/extract` | POST | Extract files from IFS |

### Utility

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/info` | GET | API information |
| `/health` | GET | Health check |

## Example Usage

### Process Firmware with Logo
```bash
curl -X POST "http://localhost:5001/api/ipc-logo" \
  -F "firmware=@original.vbf" \
  -F "logo=@custom_logo.png" \
  -o modified.vbf
```

### Analyze Firmware
```bash
curl -X POST "http://localhost:5001/api/analyze" \
  -F "firmware=@firmware.bin"
```

### Scan for Signatures
```bash
curl -X POST "http://localhost:5001/api/binwalk/scan" \
  -F "firmware=@firmware.bin"
```

## Supported File Signatures

### Archives
gzip, bzip2, xz, lzma, zlib, ZIP, RAR, 7z, TAR

### Images
PNG, JPEG, GIF, BMP, TIFF

### Executables
ELF, PE/MZ, Mach-O

### Filesystems
CramFS, SquashFS, JFFS2, UBIFS, RomFS, QNX IFS

### Automotive
VBF (Volvo Binary Format), KZB (Kanzi Binary Archive), Ford bitmaps.bin

## Architecture

```
FordFirmwareEngineeringTool/
├── Controllers/
│   └── IpcLogoController.cs
├── Services/
│   ├── VbfService.cs
│   ├── KzbService.cs
│   ├── TarService.cs
│   ├── BitmapsService.cs
│   ├── SpritesheetService.cs
│   ├── LzssService.cs
│   ├── CrcService.cs
│   ├── BinwalkService.cs       # NEW
│   ├── DumpIfsService.cs       # NEW
│   └── FirmwareProcessingService.cs
├── Models/
│   ├── VbfModels.cs
│   ├── KzbModels.cs
│   ├── ProcessingModels.cs
│   ├── BinwalkModels.cs        # NEW
│   └── IfsModels.cs            # NEW
├── Program.cs
├── Dockerfile
├── azure-pipelines.yml
└── appsettings.json
```

## License

Copyright © Tester Present - Specialist Automotive Solutions
https://testerpresent.com.au
