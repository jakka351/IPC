using System.Text;
using FordFirmwareEngineeringTool.Models;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for bitmaps.bin operations
/// </summary>
public interface IBitmapsService
{
    Dictionary<string, byte[]> Extract(byte[] data);
    byte[] Build(Dictionary<string, byte[]> files, bool includeHeader = true, bool alignSections = true, bool addCrc = false);
    byte[] ReplaceKzb(byte[] bitmapsData, byte[] newKzbData);
}

/// <summary>
/// Service for handling bitmaps.bin files used in Ford IPC firmware
/// Virtual path mapping inside bitmaps.bin (fixed order):
/// - KZB:  install/bin/cluster.kzb
/// - TXT1: install/bin/cluster.kzb.txt
/// - TXT2: part_number/ifs3_part_number.txt
/// - CFG:  install/bin/cluster.kzb.cfg
/// </summary>
public class BitmapsService : IBitmapsService
{
    private static readonly byte[] BTMP_MAGIC = Encoding.ASCII.GetBytes("BTMP");
    
    private readonly ICrcService _crcService;
    private readonly ILogger<BitmapsService> _logger;
    
    public BitmapsService(ICrcService crcService, ILogger<BitmapsService> logger)
    {
        _crcService = crcService;
        _logger = logger;
    }
    
    /// <summary>
    /// Extract files from a bitmaps.bin
    /// </summary>
    public Dictionary<string, byte[]> Extract(byte[] data)
    {
        var files = new Dictionary<string, byte[]>();
        
        if (data.Length < 8)
        {
            _logger.LogWarning("bitmaps.bin too small: {Size} bytes", data.Length);
            return files;
        }
        
        int offset = 0;
        
        // Check for BTMP magic
        bool hasBtmpMagic = data.Length >= 4 &&
                           data[0] == BTMP_MAGIC[0] &&
                           data[1] == BTMP_MAGIC[1] &&
                           data[2] == BTMP_MAGIC[2] &&
                           data[3] == BTMP_MAGIC[3];
        
        if (hasBtmpMagic)
        {
            offset = 4;
            
            // Read file count
            int fileCount = (int)ReadLE32(data, offset);
            offset += 4;
            
            _logger.LogDebug("BTMP format detected, {Count} files", fileCount);
            
            // Read file table
            var entries = new List<(string path, int offset, int size)>();
            
            for (int i = 0; i < fileCount && offset < data.Length - 6; i++)
            {
                // Read path length
                int pathLen = ReadLE16(data, offset);
                offset += 2;
                
                // Read path
                string path = Encoding.UTF8.GetString(data, offset, Math.Min(pathLen, data.Length - offset));
                offset += pathLen;
                
                // Read offset and size
                int fileOffset = (int)ReadLE32(data, offset);
                offset += 4;
                int fileSize = (int)ReadLE32(data, offset);
                offset += 4;
                
                entries.Add((path, fileOffset, fileSize));
                _logger.LogDebug("Entry: {Path} @ 0x{Offset:X} ({Size} bytes)", path, fileOffset, fileSize);
            }
            
            // Extract files
            foreach (var (path, fileOffset, fileSize) in entries)
            {
                if (fileOffset >= 0 && fileOffset + fileSize <= data.Length)
                {
                    byte[] fileData = new byte[fileSize];
                    Array.Copy(data, fileOffset, fileData, 0, fileSize);
                    files[path] = fileData;
                }
            }
        }
        else
        {
            // Legacy format - try to detect structure
            _logger.LogDebug("Legacy bitmaps.bin format, attempting extraction");
            
            // Try reading as simple concatenated format with size headers
            // This is a fallback heuristic approach
            TryExtractLegacyFormat(data, files);
        }
        
        _logger.LogInformation("Extracted {Count} files from bitmaps.bin", files.Count);
        
        return files;
    }
    
    /// <summary>
    /// Build a bitmaps.bin from component files
    /// </summary>
    public byte[] Build(Dictionary<string, byte[]> files, bool includeHeader = true, bool alignSections = true, bool addCrc = false)
    {
        var output = new List<byte>();
        
        // Add BTMP magic
        output.AddRange(BTMP_MAGIC);
        
        // File count
        int fileCount = files.Count;
        output.AddRange(PutLE32((uint)fileCount));
        
        // Calculate header size to determine data offsets
        int headerSize = 4 + 4; // Magic + count
        foreach (var (path, _) in files)
        {
            byte[] pathBytes = Encoding.UTF8.GetBytes(path);
            headerSize += 2 + pathBytes.Length + 4 + 4; // path_len + path + offset + size
        }
        
        if (alignSections)
        {
            headerSize = Align4(headerSize);
        }
        
        // If legacy header is requested, add additional size table
        int legacyHeaderSize = 0;
        if (includeHeader)
        {
            if (alignSections)
            {
                headerSize = Align4(headerSize);
            }
            legacyHeaderSize = 4 + (4 * 2 * 4); // count + 4 entries (offset, size each)
            headerSize += legacyHeaderSize;
            
            if (alignSections)
            {
                headerSize = Align4(headerSize);
            }
        }
        
        // Calculate data offsets
        var entries = new List<(string path, byte[] data, int offset, int size)>();
        int currentOffset = headerSize;
        
        foreach (var (path, data) in files)
        {
            entries.Add((path, data, currentOffset, data.Length));
            currentOffset += data.Length;
            
            if (alignSections && files.Keys.ToList().IndexOf(path) < files.Count - 1)
            {
                currentOffset = Align4(currentOffset);
            }
        }
        
        // Write variable-length file table
        foreach (var (path, data, fileOffset, size) in entries)
        {
            byte[] pathBytes = Encoding.UTF8.GetBytes(path);
            output.AddRange(PutLE16((ushort)pathBytes.Length));
            output.AddRange(pathBytes);
            output.AddRange(PutLE32((uint)fileOffset));
            output.AddRange(PutLE32((uint)size));
        }
        
        // Align before legacy header
        if (alignSections)
        {
            while (output.Count % 4 != 0)
            {
                output.Add(0);
            }
        }
        
        // Write legacy header if requested
        if (includeHeader)
        {
            output.AddRange(PutLE32(4)); // Always 4 entries in legacy format
            
            for (int i = 0; i < 4; i++)
            {
                if (i < entries.Count)
                {
                    output.AddRange(PutLE32((uint)entries[i].offset));
                    output.AddRange(PutLE32((uint)entries[i].size));
                }
                else
                {
                    output.AddRange(PutLE32(0));
                    output.AddRange(PutLE32(0));
                }
            }
        }
        
        // Align data start
        if (alignSections)
        {
            while (output.Count % 4 != 0)
            {
                output.Add(0);
            }
        }
        
        // Write file data
        foreach (var (_, data, _, _) in entries)
        {
            output.AddRange(data);
            
            if (alignSections && entries.IndexOf(entries.First(e => e.data == data)) < entries.Count - 1)
            {
                while (output.Count % 4 != 0)
                {
                    output.Add(0);
                }
            }
        }
        
        // Add CRC if requested
        if (addCrc)
        {
            uint crc = _crcService.Crc32(output.ToArray());
            output.AddRange(PutLE32(crc));
            _logger.LogDebug("Added CRC32: 0x{CRC:X8}", crc);
        }
        
        _logger.LogInformation("Built bitmaps.bin: {Size} bytes, {Count} files", output.Count, fileCount);
        
        return output.ToArray();
    }
    
    /// <summary>
    /// Replace the KZB file within bitmaps.bin
    /// </summary>
    public byte[] ReplaceKzb(byte[] bitmapsData, byte[] newKzbData)
    {
        var files = Extract(bitmapsData);
        
        // Find the KZB entry
        string? kzbKey = files.Keys.FirstOrDefault(k => 
            k.EndsWith(".kzb", StringComparison.OrdinalIgnoreCase) &&
            !k.EndsWith(".kzb.txt", StringComparison.OrdinalIgnoreCase) &&
            !k.EndsWith(".kzb.cfg", StringComparison.OrdinalIgnoreCase));
        
        if (kzbKey == null)
        {
            // Use default virtual path
            kzbKey = BitmapsVirtualPaths.KZB;
        }
        
        files[kzbKey] = newKzbData;
        
        _logger.LogInformation("Replaced KZB at {Key}: {Size} bytes", kzbKey, newKzbData.Length);
        
        return Build(files);
    }
    
    #region Private Methods
    
    private void TryExtractLegacyFormat(byte[] data, Dictionary<string, byte[]> files)
    {
        // Try to read as a simple size-table format
        // First 4 bytes might be count
        if (data.Length < 4) return;
        
        int count = (int)ReadLE32(data, 0);
        
        // Sanity check
        if (count < 1 || count > 100) return;
        
        int offset = 4;
        var entries = new List<(int offset, int size)>();
        
        // Try to read offset/size pairs
        for (int i = 0; i < count && offset + 8 <= data.Length; i++)
        {
            int entryOffset = (int)ReadLE32(data, offset);
            int entrySize = (int)ReadLE32(data, offset + 4);
            offset += 8;
            
            if (entryOffset > 0 && entryOffset < data.Length && entrySize > 0 && entryOffset + entrySize <= data.Length)
            {
                entries.Add((entryOffset, entrySize));
            }
        }
        
        // Extract using detected entries
        string[] defaultNames = { "cluster.kzb", "cluster.kzb.txt", "ifs3_part_number.txt", "cluster.kzb.cfg" };
        
        for (int i = 0; i < entries.Count && i < defaultNames.Length; i++)
        {
            var (entryOffset, entrySize) = entries[i];
            byte[] fileData = new byte[entrySize];
            Array.Copy(data, entryOffset, fileData, 0, entrySize);
            files[defaultNames[i]] = fileData;
        }
    }
    
    private static uint ReadLE32(byte[] data, int offset)
    {
        return BitConverter.ToUInt32(data, offset);
    }
    
    private static ushort ReadLE16(byte[] data, int offset)
    {
        return BitConverter.ToUInt16(data, offset);
    }
    
    private static byte[] PutLE32(uint value)
    {
        return BitConverter.GetBytes(value);
    }
    
    private static byte[] PutLE16(ushort value)
    {
        return BitConverter.GetBytes(value);
    }
    
    private static int Align4(int value)
    {
        return (value + 3) & ~3;
    }
    
    #endregion
}
