namespace FordFirmwareEngineeringTool.Models;

/// <summary>
/// QNX IFS compression types
/// </summary>
public enum IfsCompressionType
{
    None = 0,
    Zlib = 1,
    Lzo = 2,
    Ucl = 3
}

/// <summary>
/// QNX Startup Header structure (256 bytes)
/// </summary>
public class IfsStartupHeader
{
    public const int SIZE = 256;
    public const uint SIGNATURE = 0x00ff7eeb;
    
    public uint SignatureValue { get; set; }
    public ushort Version { get; set; }
    public byte Flags1 { get; set; }
    public byte Flags2 { get; set; }
    public ushort HeaderSize { get; set; }
    public ushort Machine { get; set; }
    public uint StartupVaddr { get; set; }
    public uint PaddrBias { get; set; }
    public uint ImagePaddr { get; set; }
    public uint RamPaddr { get; set; }
    public uint RamSize { get; set; }
    public uint StartupSize { get; set; }
    public uint StoredSize { get; set; }
    public uint ImagefsPaddr { get; set; }
    public uint ImagefsSize { get; set; }
    public ushort PrebootSize { get; set; }
    
    public bool IsValid => SignatureValue == SIGNATURE;
    
    public static IfsStartupHeader Parse(byte[] data, int offset = 0)
    {
        if (data.Length - offset < SIZE)
            throw new ArgumentException($"Data too small for startup header: {data.Length - offset} < {SIZE}");
        
        return new IfsStartupHeader
        {
            SignatureValue = BitConverter.ToUInt32(data, offset),
            Version = BitConverter.ToUInt16(data, offset + 4),
            Flags1 = data[offset + 6],
            Flags2 = data[offset + 7],
            HeaderSize = BitConverter.ToUInt16(data, offset + 8),
            Machine = BitConverter.ToUInt16(data, offset + 10),
            StartupVaddr = BitConverter.ToUInt32(data, offset + 12),
            PaddrBias = BitConverter.ToUInt32(data, offset + 16),
            ImagePaddr = BitConverter.ToUInt32(data, offset + 20),
            RamPaddr = BitConverter.ToUInt32(data, offset + 24),
            RamSize = BitConverter.ToUInt32(data, offset + 28),
            StartupSize = BitConverter.ToUInt32(data, offset + 32),
            StoredSize = BitConverter.ToUInt32(data, offset + 36),
            ImagefsPaddr = BitConverter.ToUInt32(data, offset + 40),
            ImagefsSize = BitConverter.ToUInt16(data, offset + 44),
            PrebootSize = BitConverter.ToUInt16(data, offset + 46)
        };
    }
}

/// <summary>
/// QNX Image Header structure
/// </summary>
public class IfsImageHeader
{
    public const int SIZE = 28;
    public static readonly byte[] SIGNATURE = "imagefs"u8.ToArray();
    
    public byte[] SignatureBytes { get; set; } = new byte[8];
    public uint Flags { get; set; }
    public uint ImageSize { get; set; }
    public uint HdrDirSize { get; set; }
    public uint DirOffset { get; set; }
    public uint BootIno { get; set; }
    public string Mountpoint { get; set; } = string.Empty;
    
    public bool IsValid => SignatureBytes.Take(7).SequenceEqual(SIGNATURE);
    
    public static IfsImageHeader Parse(byte[] data, int offset = 0)
    {
        if (data.Length - offset < SIZE)
            throw new ArgumentException($"Data too small for image header: {data.Length - offset} < {SIZE}");
        
        var header = new IfsImageHeader
        {
            SignatureBytes = data.Skip(offset).Take(8).ToArray(),
            Flags = BitConverter.ToUInt32(data, offset + 8),
            ImageSize = BitConverter.ToUInt32(data, offset + 12),
            HdrDirSize = BitConverter.ToUInt32(data, offset + 16),
            DirOffset = BitConverter.ToUInt32(data, offset + 20),
            BootIno = BitConverter.ToUInt32(data, offset + 24)
        };
        
        // Read mountpoint (null-terminated string after fixed fields)
        int mpStart = offset + SIZE;
        int mpEnd = Array.IndexOf(data, (byte)0, mpStart);
        if (mpEnd > mpStart && mpEnd < data.Length)
        {
            header.Mountpoint = System.Text.Encoding.UTF8.GetString(data, mpStart, mpEnd - mpStart);
        }
        
        return header;
    }
}

/// <summary>
/// Base class for IFS directory entries
/// </summary>
public class IfsDirent
{
    public const int BASE_SIZE = 16;
    
    public ushort Size { get; set; }
    public ushort ExtAttrOffset { get; set; }
    public ushort Ino { get; set; }
    public ushort Mode { get; set; }
    public uint Gid { get; set; }
    public uint Uid { get; set; }
    public string Path { get; set; } = string.Empty;
    
    // Mode type checks (POSIX-style)
    public bool IsRegularFile => (Mode & 0xF000) == 0x8000;
    public bool IsDirectory => (Mode & 0xF000) == 0x4000;
    public bool IsSymlink => (Mode & 0xF000) == 0xA000;
    public bool IsBlockDevice => (Mode & 0xF000) == 0x6000;
    public bool IsCharDevice => (Mode & 0xF000) == 0x2000;
    
    public static IfsDirent ParseBase(byte[] data, int offset)
    {
        return new IfsDirent
        {
            Size = BitConverter.ToUInt16(data, offset),
            ExtAttrOffset = BitConverter.ToUInt16(data, offset + 2),
            Ino = BitConverter.ToUInt16(data, offset + 4),
            Mode = BitConverter.ToUInt16(data, offset + 6),
            Gid = BitConverter.ToUInt32(data, offset + 8),
            Uid = BitConverter.ToUInt32(data, offset + 12)
        };
    }
    
    protected static string ReadPath(byte[] data, int offset)
    {
        int end = Array.IndexOf(data, (byte)0, offset);
        if (end < 0) end = data.Length;
        return System.Text.Encoding.UTF8.GetString(data, offset, end - offset);
    }
}

/// <summary>
/// IFS file entry
/// </summary>
public class IfsFile : IfsDirent
{
    public new const int BASE_SIZE = 28;
    
    public uint FileOffset { get; set; }
    public uint FileSize { get; set; }
    public uint Mtime { get; set; }
    
    public static IfsFile Parse(byte[] data, int offset)
    {
        var file = new IfsFile
        {
            Size = BitConverter.ToUInt16(data, offset),
            ExtAttrOffset = BitConverter.ToUInt16(data, offset + 2),
            Ino = BitConverter.ToUInt16(data, offset + 4),
            Mode = BitConverter.ToUInt16(data, offset + 6),
            Gid = BitConverter.ToUInt32(data, offset + 8),
            Uid = BitConverter.ToUInt32(data, offset + 12),
            FileOffset = BitConverter.ToUInt32(data, offset + 16),
            FileSize = BitConverter.ToUInt32(data, offset + 20),
            Mtime = BitConverter.ToUInt32(data, offset + 24)
        };
        
        file.Path = ReadPath(data, offset + BASE_SIZE);
        return file;
    }
}

/// <summary>
/// IFS directory entry
/// </summary>
public class IfsDirectory : IfsDirent
{
    public static IfsDirectory Parse(byte[] data, int offset)
    {
        var dir = new IfsDirectory
        {
            Size = BitConverter.ToUInt16(data, offset),
            ExtAttrOffset = BitConverter.ToUInt16(data, offset + 2),
            Ino = BitConverter.ToUInt16(data, offset + 4),
            Mode = BitConverter.ToUInt16(data, offset + 6),
            Gid = BitConverter.ToUInt32(data, offset + 8),
            Uid = BitConverter.ToUInt32(data, offset + 12)
        };
        
        dir.Path = ReadPath(data, offset + IfsDirent.BASE_SIZE);
        return dir;
    }
}

/// <summary>
/// IFS symlink entry
/// </summary>
public class IfsSymlink : IfsDirent
{
    public new const int BASE_SIZE = 18;
    
    public ushort SymOffset { get; set; }
    public string SymLink { get; set; } = string.Empty;
    
    public static IfsSymlink Parse(byte[] data, int offset)
    {
        var symlink = new IfsSymlink
        {
            Size = BitConverter.ToUInt16(data, offset),
            ExtAttrOffset = BitConverter.ToUInt16(data, offset + 2),
            Ino = BitConverter.ToUInt16(data, offset + 4),
            Mode = BitConverter.ToUInt16(data, offset + 6),
            Gid = BitConverter.ToUInt32(data, offset + 8),
            Uid = BitConverter.ToUInt32(data, offset + 12),
            SymOffset = BitConverter.ToUInt16(data, offset + 16)
        };
        
        symlink.Path = ReadPath(data, offset + BASE_SIZE);
        return symlink;
    }
}

/// <summary>
/// IFS device entry
/// </summary>
public class IfsDevice : IfsDirent
{
    public new const int BASE_SIZE = 20;
    
    public uint Dev { get; set; }
    
    public static IfsDevice Parse(byte[] data, int offset)
    {
        var device = new IfsDevice
        {
            Size = BitConverter.ToUInt16(data, offset),
            ExtAttrOffset = BitConverter.ToUInt16(data, offset + 2),
            Ino = BitConverter.ToUInt16(data, offset + 4),
            Mode = BitConverter.ToUInt16(data, offset + 6),
            Gid = BitConverter.ToUInt32(data, offset + 8),
            Uid = BitConverter.ToUInt32(data, offset + 12),
            Dev = BitConverter.ToUInt32(data, offset + 16)
        };
        
        device.Path = ReadPath(data, offset + BASE_SIZE);
        return device;
    }
}

/// <summary>
/// Parsed IFS directory entry with type info
/// </summary>
public class IfsEntry
{
    public string Type { get; set; } = string.Empty;
    public IfsDirent Entry { get; set; } = null!;
}

/// <summary>
/// Complete IFS image info
/// </summary>
public class IfsImage
{
    public string SourceFile { get; set; } = string.Empty;
    public int StartupPosition { get; set; }
    public int ImagePosition { get; set; }
    public IfsStartupHeader? StartupHeader { get; set; }
    public IfsImageHeader? ImageHeader { get; set; }
    public IfsCompressionType CompressionType { get; set; }
    public bool IsCompressed => CompressionType != IfsCompressionType.None;
    public List<IfsEntry> Entries { get; set; } = new();
    public byte[]? DecompressedData { get; set; }
}
