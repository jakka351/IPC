namespace FordFirmwareEngineeringTool.Models;

/// <summary>
/// Result of firmware processing operation
/// </summary>
public class ProcessingResult
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public string? OutputFileName { get; set; }
    public byte[]? OutputData { get; set; }
    public ProcessingLog Log { get; set; } = new();
    public ProcessingStats Stats { get; set; } = new();
}

/// <summary>
/// Processing operation log
/// </summary>
public class ProcessingLog
{
    public List<LogEntry> Entries { get; set; } = new();
    
    public void Info(string message) => Entries.Add(new LogEntry(LogLevel.Info, message));
    public void Success(string message) => Entries.Add(new LogEntry(LogLevel.Success, message));
    public void Warning(string message) => Entries.Add(new LogEntry(LogLevel.Warning, message));
    public void Error(string message) => Entries.Add(new LogEntry(LogLevel.Error, message));
}

/// <summary>
/// Single log entry
/// </summary>
public class LogEntry
{
    public DateTime Timestamp { get; set; }
    public LogLevel Level { get; set; }
    public string Message { get; set; }

    public LogEntry(LogLevel level, string message)
    {
        Timestamp = DateTime.UtcNow;
        Level = level;
        Message = message;
    }
}

/// <summary>
/// Log severity level
/// </summary>
public enum LogLevel
{
    Info,
    Success,
    Warning,
    Error
}

/// <summary>
/// Statistics from processing operation
/// </summary>
public class ProcessingStats
{
    public int VbfBlocksProcessed { get; set; }
    public int KzbFilesExtracted { get; set; }
    public int SpritesheetsModified { get; set; }
    public long OriginalSize { get; set; }
    public long OutputSize { get; set; }
    public TimeSpan ProcessingTime { get; set; }
}

/// <summary>
/// Request for IPC logo processing
/// </summary>
public class IpcLogoRequest
{
    public IFormFile? FirmwareFile { get; set; }
    public IFormFile? LogoFile { get; set; }
}

/// <summary>
/// Bitmaps.bin virtual path mapping
/// </summary>
public static class BitmapsVirtualPaths
{
    public const string KZB = "install/bin/cluster.kzb";
    public const string TXT1 = "install/bin/cluster.kzb.txt";
    public const string TXT2 = "part_number/ifs3_part_number.txt";
    public const string CFG = "install/bin/cluster.kzb.cfg";
}
