using Microsoft.AspNetCore.Mvc;
using FordFirmwareEngineeringTool.Models;
using FordFirmwareEngineeringTool.Services;

namespace FordFirmwareEngineeringTool.Controllers;

/// <summary>
/// Controller for IPC (Instrument Panel Cluster) logo processing and firmware analysis
/// </summary>
[ApiController]
[Route("api")]
public class IpcLogoController : ControllerBase
{
    private readonly IFirmwareProcessingService _processingService;
    private readonly IBinwalkService _binwalkService;
    private readonly IDumpIfsService _dumpIfsService;
    private readonly ILogger<IpcLogoController> _logger;
    private readonly IConfiguration _configuration;
    
    public IpcLogoController(
        IFirmwareProcessingService processingService,
        IBinwalkService binwalkService,
        IDumpIfsService dumpIfsService,
        ILogger<IpcLogoController> logger,
        IConfiguration configuration)
    {
        _processingService = processingService;
        _binwalkService = binwalkService;
        _dumpIfsService = dumpIfsService;
        _logger = logger;
        _configuration = configuration;
    }
    
    /// <summary>
    /// Process IPC firmware with custom logo
    /// </summary>
    /// <remarks>
    /// Accepts VBF firmware file and PNG logo, processes and returns modified VBF.
    /// 
    /// The processing pipeline:
    /// 1. Parse VBF file and extract data blocks
    /// 2. Extract TAR archive from firmware
    /// 3. Extract bitmaps.bin containing KZB archive
    /// 4. Unpack KZB archive
    /// 5. Apply logo to spritesheet images (4x4 grid)
    /// 6. Repack all archives
    /// 7. Build new VBF with modified data
    /// </remarks>
    /// <param name="firmware">VBF firmware file</param>
    /// <param name="logo">PNG logo file with transparency</param>
    /// <returns>Modified VBF file or processing result</returns>
    [HttpPost("ipc-logo")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(FileContentResult), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProcessingResult), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ProcessingResult), StatusCodes.Status500InternalServerError)]
    [RequestSizeLimit(100 * 1024 * 1024)] // 100MB
    public async Task<IActionResult> ProcessIpcLogo(
        [FromForm] IFormFile firmware,
        [FromForm] IFormFile logo)
    {
        _logger.LogInformation("IPC logo processing request received");
        
        // Validate firmware file
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new ProcessingResult
            {
                Success = false,
                ErrorMessage = "Firmware file is required"
            });
        }
        
        // Validate logo file
        if (logo == null || logo.Length == 0)
        {
            return BadRequest(new ProcessingResult
            {
                Success = false,
                ErrorMessage = "Logo file is required"
            });
        }
        
        // Validate file types
        if (!firmware.FileName.EndsWith(".vbf", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning("Non-VBF file uploaded: {FileName}", firmware.FileName);
            // Allow processing anyway, might be raw data
        }
        
        if (!logo.FileName.EndsWith(".png", StringComparison.OrdinalIgnoreCase))
        {
            return BadRequest(new ProcessingResult
            {
                Success = false,
                ErrorMessage = "Logo must be a PNG file with transparency"
            });
        }
        
        // Check file sizes
        long maxSize = _configuration.GetValue("FirmwareProcessing:MaxFileSizeMB", 100) * 1024 * 1024;
        if (firmware.Length > maxSize)
        {
            return BadRequest(new ProcessingResult
            {
                Success = false,
                ErrorMessage = $"Firmware file exceeds maximum size of {maxSize / (1024 * 1024)}MB"
            });
        }
        
        try
        {
            // Read files into memory
            byte[] firmwareData;
            byte[] logoData;
            
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            using (var ms = new MemoryStream())
            {
                await logo.CopyToAsync(ms);
                logoData = ms.ToArray();
            }
            
            _logger.LogInformation("Processing firmware: {FirmwareSize} bytes, logo: {LogoSize} bytes",
                firmwareData.Length, logoData.Length);
            
            // Process the firmware
            var result = await _processingService.ProcessIpcLogoAsync(
                firmwareData, 
                logoData,
                (progress, status) => _logger.LogDebug("Progress: {Progress}% - {Status}", progress, status));
            
            if (!result.Success || result.OutputData == null)
            {
                _logger.LogWarning("Processing failed: {Error}", result.ErrorMessage);
                return BadRequest(result);
            }
            
            _logger.LogInformation("Processing successful: {OutputSize} bytes", result.OutputData.Length);
            
            // Return the modified VBF file
            return File(
                result.OutputData,
                "application/octet-stream",
                result.OutputFileName ?? "modified_firmware.vbf");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing IPC logo request");
            
            return StatusCode(500, new ProcessingResult
            {
                Success = false,
                ErrorMessage = $"Internal server error: {ex.Message}"
            });
        }
    }
    
    /// <summary>
    /// Process IPC firmware with custom logo and return detailed result
    /// </summary>
    [HttpPost("ipc-logo/detailed")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(ProcessingResultDto), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ProcessingResult), StatusCodes.Status400BadRequest)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> ProcessIpcLogoDetailed(
        [FromForm] IFormFile firmware,
        [FromForm] IFormFile logo)
    {
        _logger.LogInformation("Detailed IPC logo processing request received");
        
        // Validate inputs
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        if (logo == null || logo.Length == 0)
        {
            return BadRequest(new { error = "Logo file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            byte[] logoData;
            
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            using (var ms = new MemoryStream())
            {
                await logo.CopyToAsync(ms);
                logoData = ms.ToArray();
            }
            
            var result = await _processingService.ProcessIpcLogoAsync(firmwareData, logoData);
            
            // Create response DTO
            var response = new ProcessingResultDto
            {
                Success = result.Success,
                ErrorMessage = result.ErrorMessage,
                OutputFileName = result.OutputFileName,
                OutputDataBase64 = result.OutputData != null ? Convert.ToBase64String(result.OutputData) : null,
                Stats = new ProcessingStatsDto
                {
                    VbfBlocksProcessed = result.Stats.VbfBlocksProcessed,
                    KzbFilesExtracted = result.Stats.KzbFilesExtracted,
                    SpritesheetsModified = result.Stats.SpritesheetsModified,
                    OriginalSize = result.Stats.OriginalSize,
                    OutputSize = result.Stats.OutputSize,
                    ProcessingTimeMs = (long)result.Stats.ProcessingTime.TotalMilliseconds
                },
                Log = result.Log.Entries.Select(e => new LogEntryDto
                {
                    Timestamp = e.Timestamp,
                    Level = e.Level.ToString(),
                    Message = e.Message
                }).ToList()
            };
            
            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in detailed processing");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Get API information
    /// </summary>
    [HttpGet("info")]
    public IActionResult GetInfo()
    {
        return Ok(new
        {
            name = "Ford Firmware Engineering Tool API",
            version = "1.0.0",
            description = "Backend API for Ford IPC custom bootsplash logo processing",
            endpoints = new[]
            {
                new { method = "POST", path = "/api/ipc-logo", description = "Process firmware with logo" },
                new { method = "POST", path = "/api/ipc-logo/detailed", description = "Process with detailed response" },
                new { method = "POST", path = "/api/analyze", description = "Analyze firmware (binwalk + dumpIFS)" },
                new { method = "POST", path = "/api/binwalk/scan", description = "Scan for file signatures" },
                new { method = "POST", path = "/api/binwalk/entropy", description = "Entropy analysis" },
                new { method = "POST", path = "/api/binwalk/extract", description = "Extract embedded files" },
                new { method = "POST", path = "/api/binwalk/hash", description = "Calculate file hashes" },
                new { method = "POST", path = "/api/dumpifs", description = "Parse QNX IFS image" },
                new { method = "POST", path = "/api/dumpifs/extract", description = "Extract files from IFS" },
                new { method = "GET", path = "/api/info", description = "API information" },
                new { method = "GET", path = "/health", description = "Health check" }
            },
            configuration = new
            {
                maxFileSizeMB = _configuration.GetValue("FirmwareProcessing:MaxFileSizeMB", 100),
                spritesheetGrid = $"{_configuration.GetValue("FirmwareProcessing:SpritesheetGridRows", 4)}x{_configuration.GetValue("FirmwareProcessing:SpritesheetGridCols", 4)}",
                logoMaxRatio = _configuration.GetValue("FirmwareProcessing:LogoMaxRatio", 0.45f)
            }
        });
    }
    
    #region Firmware Analysis Endpoints
    
    /// <summary>
    /// Comprehensive firmware analysis using binwalk and dumpIFS
    /// </summary>
    [HttpPost("analyze")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(FirmwareAnalysisResultDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> AnalyzeFirmware([FromForm] IFormFile firmware)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            _logger.LogInformation("Analyzing firmware: {Size} bytes", firmwareData.Length);
            
            var result = await _processingService.AnalyzeFirmwareAsync(firmwareData);
            
            return Ok(new FirmwareAnalysisResultDto
            {
                Success = result.Success,
                ErrorMessage = result.ErrorMessage,
                Hashes = result.Hashes,
                Entropy = result.Entropy != null ? new EntropyDto
                {
                    AverageEntropy = result.Entropy.AverageEntropy,
                    MaxEntropy = result.Entropy.MaxEntropy,
                    MinEntropy = result.Entropy.MinEntropy,
                    BlockCount = result.Entropy.BlockCount,
                    HighEntropyBlockCount = result.Entropy.HighEntropyBlocks.Count
                } : null,
                SignatureCount = result.Signatures.Count,
                Signatures = result.Signatures.Take(50).Select(s => new SignatureDto
                {
                    Offset = s.Offset,
                    Name = s.Signature.Name,
                    Description = s.Description,
                    Size = s.Size
                }).ToList(),
                IsVbf = result.VbfInfo != null,
                VbfBlockCount = result.VbfInfo?.Sections.Count ?? 0,
                IsQnxIfs = result.IfsInfo != null,
                IfsEntryCount = result.IfsInfo?.Entries.Count ?? 0,
                IfsCompression = result.IfsInfo?.CompressionType.ToString(),
                ExtractedFileCount = result.ExtractedFiles.Count,
                Log = result.Log.Entries.Select(e => new LogEntryDto
                {
                    Timestamp = e.Timestamp,
                    Level = e.Level.ToString(),
                    Message = e.Message
                }).ToList()
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing firmware");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Scan firmware for file signatures (binwalk)
    /// </summary>
    [HttpPost("binwalk/scan")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(List<SignatureDto>), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> BinwalkScan([FromForm] IFormFile firmware)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var results = await Task.Run(() => _binwalkService.ScanFile(firmwareData));
            
            return Ok(results.Select(s => new SignatureDto
            {
                Offset = s.Offset,
                Name = s.Signature.Name,
                Description = s.Description,
                Size = s.Size,
                Extension = s.Signature.Extension,
                Extractable = s.Signature.Extractable
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error scanning firmware");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Perform entropy analysis on firmware (binwalk)
    /// </summary>
    [HttpPost("binwalk/entropy")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(EntropyAnalysis), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> BinwalkEntropy(
        [FromForm] IFormFile firmware,
        [FromQuery] int blockSize = 1024)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var result = await Task.Run(() => _binwalkService.AnalyzeEntropy(firmwareData, blockSize));
            
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing entropy");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Extract embedded files from firmware (binwalk)
    /// </summary>
    [HttpPost("binwalk/extract")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(List<ExtractedFileDto>), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> BinwalkExtract(
        [FromForm] IFormFile firmware,
        [FromQuery] int minSize = 0)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var extracted = await Task.Run(() => _binwalkService.ExtractFiles(firmwareData, null, minSize));
            
            return Ok(extracted.Select(f => new ExtractedFileDto
            {
                Name = f.Name,
                Offset = f.Offset,
                Size = f.Size,
                Type = f.Type,
                DataBase64 = Convert.ToBase64String(f.Data)
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error extracting files");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Calculate file hashes (binwalk)
    /// </summary>
    [HttpPost("binwalk/hash")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(FileHashResult), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> BinwalkHash([FromForm] IFormFile firmware)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var result = await Task.Run(() => _binwalkService.GetFileHash(firmwareData));
            
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calculating hashes");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Parse QNX IFS image (dumpIFS)
    /// </summary>
    [HttpPost("dumpifs")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(IfsImageDto), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> DumpIfs([FromForm] IFormFile firmware)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var image = await Task.Run(() => _dumpIfsService.ParseIfs(firmwareData));
            
            return Ok(new IfsImageDto
            {
                StartupPosition = image.StartupPosition,
                ImagePosition = image.ImagePosition,
                CompressionType = image.CompressionType.ToString(),
                IsCompressed = image.IsCompressed,
                StartupSize = image.StartupHeader?.StartupSize ?? 0,
                StoredSize = image.StartupHeader?.StoredSize ?? 0,
                ImageSize = image.ImageHeader?.ImageSize ?? 0,
                Mountpoint = image.ImageHeader?.Mountpoint ?? "",
                EntryCount = image.Entries.Count,
                Entries = image.Entries.Select(e => new IfsEntryDto
                {
                    Type = e.Type,
                    Path = e.Entry.Path,
                    Mode = e.Entry.Mode,
                    Size = e.Entry is IfsFile file ? file.FileSize : 0,
                    Offset = e.Entry is IfsFile f ? f.FileOffset : 0
                }).ToList()
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error parsing IFS");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    /// <summary>
    /// Extract files from QNX IFS image (dumpIFS)
    /// </summary>
    [HttpPost("dumpifs/extract")]
    [Consumes("multipart/form-data")]
    [ProducesResponseType(typeof(List<ExtractedFileDto>), StatusCodes.Status200OK)]
    [RequestSizeLimit(100 * 1024 * 1024)]
    public async Task<IActionResult> DumpIfsExtract([FromForm] IFormFile firmware)
    {
        if (firmware == null || firmware.Length == 0)
        {
            return BadRequest(new { error = "Firmware file is required" });
        }
        
        try
        {
            byte[] firmwareData;
            using (var ms = new MemoryStream())
            {
                await firmware.CopyToAsync(ms);
                firmwareData = ms.ToArray();
            }
            
            var files = await Task.Run(() => _dumpIfsService.ExtractFiles(firmwareData));
            
            return Ok(files.Select(kvp => new ExtractedFileDto
            {
                Name = Path.GetFileName(kvp.Key),
                Path = kvp.Key,
                Size = kvp.Value.Length,
                Type = "ifs",
                DataBase64 = Convert.ToBase64String(kvp.Value)
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error extracting IFS files");
            return StatusCode(500, new { error = ex.Message });
        }
    }
    
    #endregion
}

/// <summary>
/// DTO for processing result with Base64-encoded data
/// </summary>
public class ProcessingResultDto
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public string? OutputFileName { get; set; }
    public string? OutputDataBase64 { get; set; }
    public ProcessingStatsDto Stats { get; set; } = new();
    public List<LogEntryDto> Log { get; set; } = new();
}

public class ProcessingStatsDto
{
    public int VbfBlocksProcessed { get; set; }
    public int KzbFilesExtracted { get; set; }
    public int SpritesheetsModified { get; set; }
    public long OriginalSize { get; set; }
    public long OutputSize { get; set; }
    public long ProcessingTimeMs { get; set; }
}

public class LogEntryDto
{
    public DateTime Timestamp { get; set; }
    public string Level { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
}

#region Analysis DTOs

public class FirmwareAnalysisResultDto
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public FileHashResult? Hashes { get; set; }
    public EntropyDto? Entropy { get; set; }
    public int SignatureCount { get; set; }
    public List<SignatureDto> Signatures { get; set; } = new();
    public bool IsVbf { get; set; }
    public int VbfBlockCount { get; set; }
    public bool IsQnxIfs { get; set; }
    public int IfsEntryCount { get; set; }
    public string? IfsCompression { get; set; }
    public int ExtractedFileCount { get; set; }
    public List<LogEntryDto> Log { get; set; } = new();
}

public class EntropyDto
{
    public double AverageEntropy { get; set; }
    public double MaxEntropy { get; set; }
    public double MinEntropy { get; set; }
    public int BlockCount { get; set; }
    public int HighEntropyBlockCount { get; set; }
}

public class SignatureDto
{
    public long Offset { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public long Size { get; set; }
    public string Extension { get; set; } = string.Empty;
    public bool Extractable { get; set; }
}

public class ExtractedFileDto
{
    public string Name { get; set; } = string.Empty;
    public string Path { get; set; } = string.Empty;
    public long Offset { get; set; }
    public long Size { get; set; }
    public string Type { get; set; } = string.Empty;
    public string DataBase64 { get; set; } = string.Empty;
}

public class IfsImageDto
{
    public int StartupPosition { get; set; }
    public int ImagePosition { get; set; }
    public string CompressionType { get; set; } = string.Empty;
    public bool IsCompressed { get; set; }
    public uint StartupSize { get; set; }
    public uint StoredSize { get; set; }
    public uint ImageSize { get; set; }
    public string Mountpoint { get; set; } = string.Empty;
    public int EntryCount { get; set; }
    public List<IfsEntryDto> Entries { get; set; } = new();
}

public class IfsEntryDto
{
    public string Type { get; set; } = string.Empty;
    public string Path { get; set; } = string.Empty;
    public ushort Mode { get; set; }
    public uint Size { get; set; }
    public uint Offset { get; set; }
}

#endregion
