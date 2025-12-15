namespace FordFirmwareEngineeringTool.Models;

/// <summary>
/// Represents an entry in a KZB archive
/// </summary>
public class KzbEntry
{
    public string Name { get; set; } = string.Empty;
    public string Path { get; set; } = string.Empty;
    public uint Address { get; set; }
    public uint Size { get; set; }
    public byte[] Data { get; set; } = Array.Empty<byte>();
    public bool IsDirectory { get; set; }
    public List<KzbEntry> Children { get; set; } = new();
}

/// <summary>
/// Represents a parsed KZB archive
/// </summary>
public class KzbArchive
{
    public string RootName { get; set; } = string.Empty;
    public bool IsKzbf { get; set; }
    public List<KzbEntry> Entries { get; set; } = new();
    public byte[] RawData { get; set; } = Array.Empty<byte>();
}

/// <summary>
/// Represents metadata for a folder in KZB
/// </summary>
public class KzbFolderNode
{
    public string Name { get; set; } = string.Empty;
    public List<KzbFolderNode> Children { get; set; } = new();
    public List<KzbElementInfo> Elements { get; set; } = new();
}

/// <summary>
/// Represents an element (file) in a KZB folder
/// </summary>
public class KzbElementInfo
{
    public string Name { get; set; } = string.Empty;
    public string DiskPath { get; set; } = string.Empty;
    public uint Size { get; set; }
    public byte[] Data { get; set; } = Array.Empty<byte>();
}

/// <summary>
/// Placeholder for folder metadata during packing
/// </summary>
public class KzbMetaFolderPlaceholder
{
    public int SizePosition { get; set; }
}

/// <summary>
/// Placeholder for element address during packing
/// </summary>
public class KzbMetaElementPlaceholder
{
    public int AddressPosition { get; set; }
    public KzbElementInfo Element { get; set; } = null!;
}
