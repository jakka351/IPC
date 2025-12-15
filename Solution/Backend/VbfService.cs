using System.Text;
using System.Text.RegularExpressions;
using FordFirmwareEngineeringTool.Models;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for VBF file operations
/// </summary>
public interface IVbfService
{
    VbfFile Parse(byte[] data);
    byte[] Build(string headerText, List<VbfBlock> blocks, VbfBuildOptions options, Action<double>? onProgress = null);
    (string headerText, Dictionary<string, object> fields, uint? fileChecksum) ParseHeader(string headerText);
    byte[] ExtractBlockData(VbfFile vbf, int blockIndex);
}

/// <summary>
/// Service for handling VBF (Volvo Binary Format) files used by Ford for firmware updates
/// </summary>
public class VbfService : IVbfService
{
    private readonly ICrcService _crcService;
    private readonly ILzssService _lzssService;
    private readonly ILogger<VbfService> _logger;
    
    private static readonly Regex HeaderFieldRegex = new(
        @"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?);",
        RegexOptions.Singleline | RegexOptions.Compiled);
    
    private static readonly Regex FileChecksumRegex = new(
        @"(file_checksum\s*=\s*)0x[0-9A-Fa-f]{8}(\s*;)",
        RegexOptions.Compiled);
    
    public VbfService(ICrcService crcService, ILzssService lzssService, ILogger<VbfService> logger)
    {
        _crcService = crcService;
        _lzssService = lzssService;
        _logger = logger;
    }
    
    /// <summary>
    /// Parse a VBF file from raw byte data
    /// </summary>
    public VbfFile Parse(byte[] data)
    {
        var vbf = new VbfFile
        {
            RawData = data
        };
        
        // Find header bounds
        var (headerStart, headerEnd) = FindHeaderBounds(data);
        vbf.HeaderEndOffset = headerEnd;
        
        // Extract header text
        vbf.HeaderText = Encoding.Latin1.GetString(data, 0, headerEnd);
        
        // Parse header fields
        var (_, fields, fileChecksum) = ParseHeader(vbf.HeaderText);
        vbf.HeaderFields = fields;
        vbf.FileChecksum = fileChecksum;
        
        // Parse data blocks
        vbf.Sections = ParseBlocks(data, headerEnd);
        
        _logger.LogInformation("Parsed VBF file: {BlockCount} blocks, header ends at 0x{HeaderEnd:X}", 
            vbf.Sections.Count, headerEnd);
        
        return vbf;
    }
    
    /// <summary>
    /// Build a VBF file from header and blocks
    /// </summary>
    public byte[] Build(string headerText, List<VbfBlock> blocks, VbfBuildOptions options, Action<double>? onProgress = null)
    {
        onProgress?.Invoke(0.0);
        
        using var output = new MemoryStream();
        
        // Process blocks - optionally compress with LZSS
        var processedBlocks = new List<(uint address, byte[] data, ushort crc16)>();
        int total = blocks.Count;
        
        for (int i = 0; i < blocks.Count; i++)
        {
            var block = blocks[i];
            var data = block.Data;
            
            if (options.UseLzss)
            {
                data = _lzssService.Compress(data, p => onProgress?.Invoke(0.25 * ((i + p) / total)));
            }
            
            ushort crc16 = _crcService.Crc16CcittFfff(data);
            processedBlocks.Add((block.Address, data, crc16));
            
            onProgress?.Invoke(0.5 * ((i + 1.0) / total));
        }
        
        // Prepare header
        byte[] headerBytes = Encoding.Latin1.GetBytes(headerText);
        
        // Build payload
        using var payloadStream = new MemoryStream();
        foreach (var (address, data, crc16) in processedBlocks)
        {
            // Write address (big-endian)
            payloadStream.WriteByte((byte)((address >> 24) & 0xFF));
            payloadStream.WriteByte((byte)((address >> 16) & 0xFF));
            payloadStream.WriteByte((byte)((address >> 8) & 0xFF));
            payloadStream.WriteByte((byte)(address & 0xFF));
            
            // Write length (big-endian)
            uint length = (uint)data.Length;
            payloadStream.WriteByte((byte)((length >> 24) & 0xFF));
            payloadStream.WriteByte((byte)((length >> 16) & 0xFF));
            payloadStream.WriteByte((byte)((length >> 8) & 0xFF));
            payloadStream.WriteByte((byte)(length & 0xFF));
            
            // Write data
            payloadStream.Write(data, 0, data.Length);
            
            // Write CRC16 (big-endian)
            payloadStream.WriteByte((byte)((crc16 >> 8) & 0xFF));
            payloadStream.WriteByte((byte)(crc16 & 0xFF));
        }
        
        byte[] payloadBytes = payloadStream.ToArray();
        
        onProgress?.Invoke(0.7);
        
        // Calculate and insert file checksum if requested
        byte[] finalHeader = headerBytes;
        if (options.ComputeFileChecksum)
        {
            uint crc32;
            
            switch (options.CrcScope)
            {
                case VbfCrcScope.PayloadOnly:
                    crc32 = _crcService.Crc32(payloadBytes);
                    finalHeader = InsertFileChecksum(headerBytes, crc32);
                    break;
                    
                case VbfCrcScope.HeaderOnly:
                    crc32 = _crcService.Crc32(headerBytes);
                    finalHeader = InsertFileChecksum(headerBytes, crc32);
                    break;
                    
                case VbfCrcScope.WholeFileZeroedField:
                default:
                    // First insert zeroed checksum, calculate CRC over whole file, then update
                    byte[] tempHeader = InsertFileChecksum(headerBytes, 0);
                    byte[] tempFile = CombineArrays(tempHeader, payloadBytes);
                    crc32 = _crcService.Crc32(tempFile);
                    finalHeader = InsertFileChecksum(headerBytes, crc32);
                    break;
            }
        }
        
        onProgress?.Invoke(0.85);
        
        // Combine header and payload
        output.Write(finalHeader, 0, finalHeader.Length);
        output.Write(payloadBytes, 0, payloadBytes.Length);
        
        onProgress?.Invoke(1.0);
        
        return output.ToArray();
    }
    
    /// <summary>
    /// Parse header fields from header text
    /// </summary>
    public (string headerText, Dictionary<string, object> fields, uint? fileChecksum) ParseHeader(string headerText)
    {
        // Remove comments
        var lines = headerText.Split('\n')
            .Select(line => line.Contains("//") ? line.Split("//")[0] : line);
        string cleanedText = string.Join("\n", lines);
        
        var fields = new Dictionary<string, object>();
        uint? fileChecksum = null;
        
        foreach (Match match in HeaderFieldRegex.Matches(cleanedText))
        {
            string key = match.Groups[1].Value;
            string value = match.Groups[2].Value.Trim();
            
            // Handle array values
            if (value.StartsWith("{") && value.EndsWith("}"))
            {
                fields[key] = value[1..^1].Trim();
                continue;
            }
            
            // Handle quoted strings
            if (value.StartsWith("\"") && value.EndsWith("\""))
            {
                fields[key] = value[1..^1];
                continue;
            }
            
            // Handle hex values
            if (value.ToLower().StartsWith("0x"))
            {
                if (uint.TryParse(value[2..], System.Globalization.NumberStyles.HexNumber, null, out uint hexVal))
                {
                    fields[key] = hexVal;
                    if (key.Equals("file_checksum", StringComparison.OrdinalIgnoreCase))
                    {
                        fileChecksum = hexVal;
                    }
                    continue;
                }
            }
            
            // Handle numeric values
            if (value.Contains("."))
            {
                if (double.TryParse(value, out double dblVal))
                {
                    fields[key] = dblVal;
                    continue;
                }
            }
            else if (int.TryParse(value, out int intVal))
            {
                fields[key] = intVal;
                continue;
            }
            
            fields[key] = value;
        }
        
        return (headerText, fields, fileChecksum);
    }
    
    /// <summary>
    /// Extract raw data from a specific block
    /// </summary>
    public byte[] ExtractBlockData(VbfFile vbf, int blockIndex)
    {
        if (blockIndex < 0 || blockIndex >= vbf.Sections.Count)
            throw new ArgumentOutOfRangeException(nameof(blockIndex));
        
        var section = vbf.Sections[blockIndex];
        return section.Data.ToArray();
    }
    
    #region Private Methods
    
    private (int start, int end) FindHeaderBounds(byte[] data)
    {
        string content = Encoding.Latin1.GetString(data);
        string lowerContent = content.ToLower();
        
        // Find 'header' keyword
        int headerIdx = lowerContent.IndexOf("header");
        if (headerIdx < 0)
        {
            // Try to find 'vbf_version' as fallback
            int vbfVersionIdx = lowerContent.IndexOf("vbf_version");
            if (vbfVersionIdx >= 0)
            {
                int openBrace = lowerContent.IndexOf('{', vbfVersionIdx);
                if (openBrace >= 0)
                {
                    int closeBrace = MatchBrace(content, openBrace);
                    if (closeBrace >= 0)
                    {
                        return (vbfVersionIdx, closeBrace + 1);
                    }
                }
            }
            throw new InvalidDataException("No 'header' keyword found in VBF file");
        }
        
        int openBraceIdx = lowerContent.IndexOf('{', headerIdx);
        if (openBraceIdx < 0)
            throw new InvalidDataException("Found 'header' but no opening '{'");
        
        int closeBraceIdx = MatchBrace(content, openBraceIdx);
        if (closeBraceIdx < 0)
            throw new InvalidDataException("Header brace matching failed");
        
        return (headerIdx, closeBraceIdx + 1);
    }
    
    private int MatchBrace(string text, int openBracePos)
    {
        int depth = 0;
        bool inString = false;
        bool escaped = false;
        
        for (int i = openBracePos; i < text.Length; i++)
        {
            char c = text[i];
            
            if (inString)
            {
                if (escaped)
                {
                    escaped = false;
                    continue;
                }
                if (c == '\\')
                {
                    escaped = true;
                    continue;
                }
                if (c == '"')
                {
                    inString = false;
                }
                continue;
            }
            
            if (c == '"')
            {
                inString = true;
                continue;
            }
            
            if (c == '{')
            {
                depth++;
                continue;
            }
            
            if (c == '}')
            {
                depth--;
                if (depth == 0)
                {
                    return i;
                }
            }
        }
        
        return -1;
    }
    
    private List<VbfSection> ParseBlocks(byte[] data, int startOffset)
    {
        var sections = new List<VbfSection>();
        int pos = startOffset;
        int idx = 1;
        const int minHeaderSize = 4 + 4 + 2; // address + length + crc
        
        while (pos + minHeaderSize <= data.Length)
        {
            // Read address (big-endian)
            uint address = (uint)((data[pos] << 24) | (data[pos + 1] << 16) | (data[pos + 2] << 8) | data[pos + 3]);
            pos += 4;
            
            // Read length (big-endian)
            uint length = (uint)((data[pos] << 24) | (data[pos + 1] << 16) | (data[pos + 2] << 8) | data[pos + 3]);
            pos += 4;
            
            // Validate length
            if (length == 0 || pos + length + 2 > data.Length)
                break;
            
            // Read data
            int dataOffset = pos;
            byte[] blockData = new byte[length];
            Array.Copy(data, pos, blockData, 0, (int)length);
            pos += (int)length;
            
            // Read stored CRC (big-endian)
            ushort crcStored = (ushort)((data[pos] << 8) | data[pos + 1]);
            pos += 2;
            
            // Calculate CRC
            ushort crcCalc = _crcService.Crc16CcittFfff(blockData);
            
            sections.Add(new VbfSection
            {
                Index = idx++,
                StartAddress = address,
                Length = length,
                DataOffset = dataOffset,
                CrcStored = crcStored,
                CrcCalculated = crcCalc,
                Data = blockData
            });
        }
        
        return sections;
    }
    
    private byte[] InsertFileChecksum(byte[] headerBytes, uint crc)
    {
        string headerText = Encoding.Latin1.GetString(headerBytes);
        
        // Check if file_checksum field exists
        if (FileChecksumRegex.IsMatch(headerText))
        {
            // Update existing field
            string newHeader = FileChecksumRegex.Replace(headerText, $"${{1}}0x{crc:X8}${{2}}");
            return Encoding.Latin1.GetBytes(newHeader);
        }
        
        // Insert new field before closing brace
        int closeBrace = headerText.LastIndexOf('}');
        if (closeBrace >= 0)
        {
            string lineEnding = headerText.Contains("\r\n") ? "\r\n" : "\n";
            string before = headerText[..closeBrace].TrimEnd();
            string after = headerText[closeBrace..];
            string insertion = $"{lineEnding}    file_checksum = 0x{crc:X8};{lineEnding}";
            string newHeader = $"{before}{insertion}{after}";
            return Encoding.Latin1.GetBytes(newHeader);
        }
        
        return headerBytes;
    }
    
    private static byte[] CombineArrays(byte[] a, byte[] b)
    {
        byte[] result = new byte[a.Length + b.Length];
        Array.Copy(a, 0, result, 0, a.Length);
        Array.Copy(b, 0, result, a.Length, b.Length);
        return result;
    }
    
    #endregion
}
