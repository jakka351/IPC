namespace FordFirmwareEngineeringTool.Models;

/// <summary>
/// Represents a data section/block within a VBF file
/// </summary>
public class VbfSection
{
    public int Index { get; set; }
    public uint StartAddress { get; set; }
    public uint Length { get; set; }
    public int DataOffset { get; set; }
    public ushort CrcStored { get; set; }
    public ushort CrcCalculated { get; set; }
    public byte[] Data { get; set; } = Array.Empty<byte>();
    
    public bool IsCrcValid => CrcStored == CrcCalculated;
}

/// <summary>
/// Represents a parsed VBF file
/// </summary>
public class VbfFile
{
    public string FilePath { get; set; } = string.Empty;
    public string HeaderText { get; set; } = string.Empty;
    public int HeaderEndOffset { get; set; }
    public Dictionary<string, object> HeaderFields { get; set; } = new();
    public uint? FileChecksum { get; set; }
    public List<VbfSection> Sections { get; set; } = new();
    public byte[] RawData { get; set; } = Array.Empty<byte>();
}

/// <summary>
/// Options for building a VBF file
/// </summary>
public class VbfBuildOptions
{
    public bool UseLzss { get; set; } = false;
    public bool ComputeFileChecksum { get; set; } = true;
    public VbfCrcScope CrcScope { get; set; } = VbfCrcScope.WholeFileZeroedField;
}

/// <summary>
/// Scope for CRC calculation in VBF files
/// </summary>
public enum VbfCrcScope
{
    WholeFileZeroedField,
    PayloadOnly,
    HeaderOnly
}

/// <summary>
/// Block to be included in a VBF file
/// </summary>
public class VbfBlock
{
    public uint Address { get; set; }
    public byte[] Data { get; set; } = Array.Empty<byte>();
}
