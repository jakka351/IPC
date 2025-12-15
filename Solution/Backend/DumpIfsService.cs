using System.IO.Compression;
using System.Text;
using FordFirmwareEngineeringTool.Models;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for QNX IFS (Image File System) operations
/// </summary>
public interface IDumpIfsService
{
    IfsImage ParseIfs(byte[] data);
    Dictionary<string, byte[]> ExtractFiles(byte[] data);
    Dictionary<string, byte[]> ExtractFiles(IfsImage image, byte[] data);
    byte[] DecompressImage(byte[] data, IfsCompressionType compressionType);
    int FindStartupHeader(byte[] data, bool zeroCheck = true);
    int FindImageHeader(byte[] data, int startPos = 0);
}

/// <summary>
/// QNX IFS (Image File System) parser and extractor
/// Port of dumpifs utility for Windows/C#
/// </summary>
public class DumpIfsService : IDumpIfsService
{
    private readonly ILogger<DumpIfsService> _logger;
    
    public DumpIfsService(ILogger<DumpIfsService> logger)
    {
        _logger = logger;
    }
    
    /// <summary>
    /// Parse a QNX IFS image from raw data
    /// </summary>
    public IfsImage ParseIfs(byte[] data)
    {
        var image = new IfsImage();
        
        _logger.LogDebug("Parsing IFS image ({Size} bytes)", data.Length);
        
        // Find startup header
        int startupPos = FindStartupHeader(data);
        if (startupPos < 0)
        {
            throw new InvalidDataException("Could not find QNX startup header");
        }
        
        image.StartupPosition = startupPos;
        _logger.LogDebug("Found startup header at 0x{Offset:X}", startupPos);
        
        // Parse startup header
        image.StartupHeader = IfsStartupHeader.Parse(data, startupPos);
        if (!image.StartupHeader.IsValid)
        {
            throw new InvalidDataException($"Invalid startup header signature: 0x{image.StartupHeader.SignatureValue:X}");
        }
        
        _logger.LogDebug("Startup size: {Size} (0x{Size:X})", 
            image.StartupHeader.StartupSize, image.StartupHeader.StartupSize);
        _logger.LogDebug("Stored size: {Size} (0x{Size:X})", 
            image.StartupHeader.StoredSize, image.StartupHeader.StoredSize);
        
        // Check for compression
        int compStart = startupPos + (int)image.StartupHeader.StartupSize;
        image.CompressionType = DetectCompression(data, compStart);
        
        if (image.IsCompressed)
        {
            _logger.LogDebug("Detected compression: {Type}", image.CompressionType);
            
            // Decompress the image
            int compressedSize = (int)(image.StartupHeader.StoredSize - image.StartupHeader.StartupSize);
            byte[] compressedData = new byte[compressedSize];
            Array.Copy(data, compStart, compressedData, 0, compressedSize);
            
            try
            {
                image.DecompressedData = DecompressImage(compressedData, image.CompressionType);
                _logger.LogDebug("Decompressed {CompSize} -> {DecompSize} bytes",
                    compressedSize, image.DecompressedData.Length);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Decompression failed, will try to parse raw data");
            }
        }
        
        // Find image filesystem header
        byte[] searchData = image.DecompressedData ?? data;
        int searchStart = image.IsCompressed ? 0 : startupPos + (int)image.StartupHeader.StartupSize;
        
        int imagePos = FindImageHeader(searchData, searchStart);
        if (imagePos < 0)
        {
            throw new InvalidDataException("Could not find image filesystem header");
        }
        
        image.ImagePosition = imagePos;
        _logger.LogDebug("Found image header at 0x{Offset:X}", imagePos);
        
        // Parse image header
        image.ImageHeader = IfsImageHeader.Parse(searchData, imagePos);
        if (!image.ImageHeader.IsValid)
        {
            throw new InvalidDataException($"Invalid image header signature");
        }
        
        _logger.LogDebug("Image size: {Size}, Dir offset: 0x{DirOffset:X}, Dir size: {DirSize}",
            image.ImageHeader.ImageSize, image.ImageHeader.DirOffset, image.ImageHeader.HdrDirSize);
        
        // Parse directory
        int dirOffset = imagePos + (int)image.ImageHeader.DirOffset;
        if (dirOffset + image.ImageHeader.HdrDirSize > searchData.Length)
        {
            throw new InvalidDataException("Directory offset exceeds data size");
        }
        
        byte[] dirData = new byte[image.ImageHeader.HdrDirSize];
        Array.Copy(searchData, dirOffset, dirData, 0, (int)image.ImageHeader.HdrDirSize);
        
        image.Entries = ParseDirectory(dirData);
        _logger.LogDebug("Parsed {Count} directory entries", image.Entries.Count);
        
        return image;
    }
    
    /// <summary>
    /// Extract all files from IFS data
    /// </summary>
    public Dictionary<string, byte[]> ExtractFiles(byte[] data)
    {
        var image = ParseIfs(data);
        return ExtractFiles(image, data);
    }
    
    /// <summary>
    /// Extract files from a parsed IFS image
    /// </summary>
    public Dictionary<string, byte[]> ExtractFiles(IfsImage image, byte[] data)
    {
        var files = new Dictionary<string, byte[]>();
        
        byte[] sourceData = image.DecompressedData ?? data;
        int baseOffset = image.ImagePosition;
        
        foreach (var entry in image.Entries)
        {
            if (entry.Type != "file")
                continue;
            
            if (entry.Entry is not IfsFile file)
                continue;
            
            if (file.FileSize == 0)
                continue;
            
            int fileOffset = baseOffset + (int)file.FileOffset;
            
            if (fileOffset + file.FileSize > sourceData.Length)
            {
                _logger.LogWarning("File {Path} exceeds data bounds, skipping", file.Path);
                continue;
            }
            
            byte[] fileData = new byte[file.FileSize];
            Array.Copy(sourceData, fileOffset, fileData, 0, (int)file.FileSize);
            
            files[file.Path] = fileData;
            _logger.LogDebug("Extracted: {Path} ({Size} bytes)", file.Path, file.FileSize);
        }
        
        return files;
    }
    
    /// <summary>
    /// Find QNX startup header in data
    /// </summary>
    public int FindStartupHeader(byte[] data, bool zeroCheck = true)
    {
        int searchLimit = Math.Min(data.Length, 1024 * 1024); // Search first 1MB
        
        if (zeroCheck)
        {
            // Look for sequence of zeros followed by signature
            for (int pos = 0; pos < searchLimit - 512; pos++)
            {
                // Check for at least 8 zero bytes
                bool hasZeros = true;
                for (int i = 0; i < 8 && hasZeros; i++)
                {
                    if (data[pos + i] != 0)
                        hasZeros = false;
                }
                
                if (hasZeros)
                {
                    // Check for signature after zeros
                    for (int checkPos = pos + 8; checkPos < Math.Min(pos + 512, searchLimit - 4); checkPos += 4)
                    {
                        uint sig = BitConverter.ToUInt32(data, checkPos);
                        if (sig == IfsStartupHeader.SIGNATURE)
                        {
                            return checkPos;
                        }
                    }
                }
            }
        }
        
        // Fallback: direct signature search
        for (int pos = 0; pos < searchLimit - 4; pos += 4)
        {
            uint sig = BitConverter.ToUInt32(data, pos);
            if (sig == IfsStartupHeader.SIGNATURE)
            {
                return pos;
            }
        }
        
        return -1;
    }
    
    /// <summary>
    /// Find image filesystem header
    /// </summary>
    public int FindImageHeader(byte[] data, int startPos = 0)
    {
        int searchLimit = Math.Min(data.Length, startPos + 1024 * 1024);
        
        for (int pos = startPos; pos < searchLimit - 8; pos++)
        {
            bool match = true;
            for (int i = 0; i < IfsImageHeader.SIGNATURE.Length && match; i++)
            {
                if (data[pos + i] != IfsImageHeader.SIGNATURE[i])
                    match = false;
            }
            
            if (match)
                return pos;
        }
        
        return -1;
    }
    
    /// <summary>
    /// Decompress IFS image data
    /// </summary>
    public byte[] DecompressImage(byte[] data, IfsCompressionType compressionType)
    {
        switch (compressionType)
        {
            case IfsCompressionType.None:
                return data;
                
            case IfsCompressionType.Zlib:
                return DecompressZlib(data);
                
            case IfsCompressionType.Lzo:
                return DecompressLzo(data);
                
            case IfsCompressionType.Ucl:
                return DecompressUcl(data);
                
            default:
                throw new NotSupportedException($"Unsupported compression type: {compressionType}");
        }
    }
    
    #region Private Methods
    
    /// <summary>
    /// Detect compression type from data
    /// </summary>
    private IfsCompressionType DetectCompression(byte[] data, int offset)
    {
        if (offset + 2 > data.Length)
            return IfsCompressionType.None;
        
        // ZLIB magic bytes
        if ((data[offset] == 0x78 && data[offset + 1] == 0x9C) ||
            (data[offset] == 0x78 && data[offset + 1] == 0xDA) ||
            (data[offset] == 0x78 && data[offset + 1] == 0x01))
        {
            return IfsCompressionType.Zlib;
        }
        
        // LZO typically starts with different patterns
        // This is heuristic-based since LZO has no standard magic
        
        return IfsCompressionType.None;
    }
    
    /// <summary>
    /// Decompress ZLIB data
    /// </summary>
    private byte[] DecompressZlib(byte[] data)
    {
        // Skip ZLIB header (2 bytes) and use DeflateStream
        using var input = new MemoryStream(data, 2, data.Length - 2);
        using var deflate = new DeflateStream(input, CompressionMode.Decompress);
        using var output = new MemoryStream();
        
        deflate.CopyTo(output);
        return output.ToArray();
    }
    
    /// <summary>
    /// Decompress LZO data (basic implementation)
    /// </summary>
    private byte[] DecompressLzo(byte[] data)
    {
        // LZO decompression requires specialized library
        // For now, return raw data with warning
        _logger.LogWarning("LZO decompression not fully implemented, returning raw data");
        return data;
    }
    
    /// <summary>
    /// Decompress UCL data (basic implementation)
    /// </summary>
    private byte[] DecompressUcl(byte[] data)
    {
        // UCL decompression requires specialized library
        _logger.LogWarning("UCL decompression not fully implemented, returning raw data");
        return data;
    }
    
    /// <summary>
    /// Parse IFS directory structure
    /// </summary>
    private List<IfsEntry> ParseDirectory(byte[] dirData)
    {
        var entries = new List<IfsEntry>();
        int offset = 0;
        
        while (offset < dirData.Length - IfsDirent.BASE_SIZE)
        {
            // Peek at size
            ushort size = BitConverter.ToUInt16(dirData, offset);
            if (size == 0 || size == 0xFFFF)
                break;
            
            if (offset + size > dirData.Length)
                break;
            
            // Peek at mode to determine type
            ushort mode = BitConverter.ToUInt16(dirData, offset + 6);
            
            try
            {
                IfsEntry entry;
                
                if (IsRegularFile(mode))
                {
                    var file = IfsFile.Parse(dirData, offset);
                    entry = new IfsEntry { Type = "file", Entry = file };
                }
                else if (IsDirectory(mode))
                {
                    var dir = IfsDirectory.Parse(dirData, offset);
                    entry = new IfsEntry { Type = "dir", Entry = dir };
                }
                else if (IsSymlink(mode))
                {
                    var symlink = IfsSymlink.Parse(dirData, offset);
                    entry = new IfsEntry { Type = "symlink", Entry = symlink };
                }
                else if (IsBlockDevice(mode) || IsCharDevice(mode))
                {
                    var device = IfsDevice.Parse(dirData, offset);
                    entry = new IfsEntry { Type = "device", Entry = device };
                }
                else
                {
                    var dirent = IfsDirent.ParseBase(dirData, offset);
                    dirent.Path = ReadPath(dirData, offset + IfsDirent.BASE_SIZE);
                    entry = new IfsEntry { Type = "unknown", Entry = dirent };
                }
                
                entries.Add(entry);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to parse entry at offset {Offset}", offset);
            }
            
            offset += size;
        }
        
        return entries;
    }
    
    private static bool IsRegularFile(ushort mode) => (mode & 0xF000) == 0x8000;
    private static bool IsDirectory(ushort mode) => (mode & 0xF000) == 0x4000;
    private static bool IsSymlink(ushort mode) => (mode & 0xF000) == 0xA000;
    private static bool IsBlockDevice(ushort mode) => (mode & 0xF000) == 0x6000;
    private static bool IsCharDevice(ushort mode) => (mode & 0xF000) == 0x2000;
    
    private static string ReadPath(byte[] data, int offset)
    {
        int end = Array.IndexOf(data, (byte)0, offset);
        if (end < 0) end = data.Length;
        if (end <= offset) return string.Empty;
        return Encoding.UTF8.GetString(data, offset, end - offset);
    }
    
    #endregion
}
