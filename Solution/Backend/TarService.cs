using ICSharpCode.SharpZipLib.Tar;
using ICSharpCode.SharpZipLib.GZip;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for TAR archive operations
/// </summary>
public interface ITarService
{
    Dictionary<string, byte[]> Extract(byte[] data);
    byte[] Create(Dictionary<string, byte[]> files);
}

/// <summary>
/// TAR archive handling service using SharpZipLib
/// </summary>
public class TarService : ITarService
{
    private readonly ILogger<TarService> _logger;

    public TarService(ILogger<TarService> logger)
    {
        _logger = logger;
    }

    /// <summary>
    /// Extract files from TAR archive (handles gzip compressed)
    /// </summary>
    public Dictionary<string, byte[]> Extract(byte[] data)
    {
        var files = new Dictionary<string, byte[]>();

        using var inputStream = new MemoryStream(data);
        Stream tarStream;

        // Check for gzip magic
        if (data.Length >= 2 && data[0] == 0x1F && data[1] == 0x8B)
        {
            _logger.LogDebug("Detected gzip-compressed TAR");
            tarStream = new GZipInputStream(inputStream);
        }
        else
        {
            tarStream = inputStream;
        }

        using var archive = TarArchive.CreateInputTarArchive(tarStream, System.Text.Encoding.UTF8);

        // We need to extract to a temp location and read back
        var tempDir = Path.Combine(Path.GetTempPath(), $"tar_extract_{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        try
        {
            archive.ExtractContents(tempDir);

            // Read all extracted files
            foreach (var filePath in Directory.GetFiles(tempDir, "*", SearchOption.AllDirectories))
            {
                var relativePath = Path.GetRelativePath(tempDir, filePath).Replace('\\', '/');
                files[relativePath] = File.ReadAllBytes(filePath);
                _logger.LogDebug("Extracted: {Path} ({Size} bytes)", relativePath, files[relativePath].Length);
            }
        }
        finally
        {
            // Cleanup temp directory
            try
            {
                Directory.Delete(tempDir, true);
            }
            catch { }
        }

        return files;
    }

    /// <summary>
    /// Create TAR archive from files
    /// </summary>
    public byte[] Create(Dictionary<string, byte[]> files)
    {
        using var outputStream = new MemoryStream();
        using var tarOutput = new TarOutputStream(outputStream, System.Text.Encoding.UTF8);

        foreach (var (path, data) in files)
        {
            var entry = TarEntry.CreateTarEntry(path);
            entry.Size = data.Length;
            entry.ModTime = DateTime.UtcNow;

            tarOutput.PutNextEntry(entry);
            tarOutput.Write(data, 0, data.Length);
            tarOutput.CloseEntry();

            _logger.LogDebug("Added to TAR: {Path} ({Size} bytes)", path, data.Length);
        }

        tarOutput.Close();
        return outputStream.ToArray();
    }
}