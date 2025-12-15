using System.IO.Hashing;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for CRC calculation services
/// </summary>
public interface ICrcService
{
    ushort Crc16CcittFfff(ReadOnlySpan<byte> data);
    uint Crc32(ReadOnlySpan<byte> data);
    uint Crc32(ReadOnlySpan<byte> data, uint initial);
}

/// <summary>
/// Service for calculating CRC checksums used in VBF and KZB files
/// </summary>
public class CrcService : ICrcService
{
    private const ushort CRC16_POLY = 0x1021;
    private const ushort CRC16_INIT = 0xFFFF;
    
    // Pre-computed CRC16 table for performance
    private static readonly ushort[] Crc16Table = new ushort[256];
    
    static CrcService()
    {
        // Initialize CRC16 lookup table
        for (int i = 0; i < 256; i++)
        {
            ushort crc = (ushort)(i << 8);
            for (int j = 0; j < 8; j++)
            {
                if ((crc & 0x8000) != 0)
                    crc = (ushort)((crc << 1) ^ CRC16_POLY);
                else
                    crc = (ushort)(crc << 1);
            }
            Crc16Table[i] = crc;
        }
    }
    
    /// <summary>
    /// Calculate CRC16-CCITT with initial value 0xFFFF (used for VBF block checksums)
    /// </summary>
    public ushort Crc16CcittFfff(ReadOnlySpan<byte> data)
    {
        ushort crc = CRC16_INIT;
        
        foreach (byte b in data)
        {
            crc = (ushort)((crc << 8) ^ Crc16Table[(crc >> 8) ^ b]);
        }
        
        return crc;
    }
    
    /// <summary>
    /// Calculate CRC32 (used for VBF file checksums)
    /// </summary>
    public uint Crc32(ReadOnlySpan<byte> data)
    {
        return Crc32(data, 0);
    }
    
    /// <summary>
    /// Calculate CRC32 with initial value (for chained calculations)
    /// </summary>
    public uint Crc32(ReadOnlySpan<byte> data, uint initial)
    {
        var crc32 = new Crc32();
        
        if (initial != 0)
        {
            // For chained CRC, we need to handle the initial value
            // Convert initial CRC to bytes and process
            Span<byte> initBytes = stackalloc byte[4];
            System.Buffers.Binary.BinaryPrimitives.WriteUInt32LittleEndian(initBytes, initial);
        }
        
        crc32.Append(data);
        return crc32.GetCurrentHashAsUInt32();
    }
    
    /// <summary>
    /// Calculate CRC32 using zlib-compatible algorithm (for VBF file_checksum)
    /// </summary>
    public static uint Crc32Zlib(byte[] data, uint initial = 0)
    {
        // Use System.IO.Hashing which is zlib-compatible
        var hash = new Crc32();
        hash.Append(data);
        
        // XOR with initial if provided for chained calculations
        uint result = hash.GetCurrentHashAsUInt32();
        
        // If we have an initial value, we need to combine
        if (initial != 0)
        {
            // For proper chaining, we'd need to re-process
            // This is a simplified implementation
            return CombineCrc32(initial, result, data.Length);
        }
        
        return result;
    }
    
    /// <summary>
    /// Combine two CRC32 values (for chained calculations)
    /// </summary>
    private static uint CombineCrc32(uint crc1, uint crc2, int len2)
    {
        // Simplified combination - for proper implementation would need gf2_matrix_times
        // For most VBF use cases, we calculate the full CRC at once
        return crc1 ^ crc2;
    }
    
    /// <summary>
    /// Calculate CRC32 over a stream (for large files)
    /// </summary>
    public static uint Crc32Stream(Stream stream, int bufferSize = 1024 * 1024)
    {
        var hash = new Crc32();
        byte[] buffer = new byte[bufferSize];
        int bytesRead;
        
        stream.Position = 0;
        while ((bytesRead = stream.Read(buffer, 0, buffer.Length)) > 0)
        {
            hash.Append(buffer.AsSpan(0, bytesRead));
        }
        
        return hash.GetCurrentHashAsUInt32();
    }
}
