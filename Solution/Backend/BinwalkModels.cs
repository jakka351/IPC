namespace FordFirmwareEngineeringTool.Models;

/// <summary>
/// File signature definition for binwalk scanning
/// </summary>
public class FileSignature
{
    public string Name { get; set; } = string.Empty;
    public byte[] Magic { get; set; } = Array.Empty<byte>();
    public byte[]? MagicMask { get; set; }
    public int Offset { get; set; } = 0;
    public string Description { get; set; } = string.Empty;
    public string Extension { get; set; } = string.Empty;
    public Func<byte[], int, long>? SizeCalculator { get; set; }
    public bool Extractable { get; set; } = true;
}

/// <summary>
/// Result of a signature scan
/// </summary>
public class SignatureScanResult
{
    public long Offset { get; set; }
    public FileSignature Signature { get; set; } = null!;
    public long Size { get; set; }
    public string Description { get; set; } = string.Empty;
    public byte[]? ExtractedData { get; set; }
}

/// <summary>
/// Entropy analysis result
/// </summary>
public class EntropyAnalysis
{
    public double AverageEntropy { get; set; }
    public double MaxEntropy { get; set; }
    public double MinEntropy { get; set; }
    public int BlockCount { get; set; }
    public List<double> EntropyValues { get; set; } = new();
    public List<EntropyBlock> HighEntropyBlocks { get; set; } = new();
}

/// <summary>
/// Single entropy block
/// </summary>
public class EntropyBlock
{
    public long Offset { get; set; }
    public double Entropy { get; set; }
    public string Description { get; set; } = string.Empty;
}

/// <summary>
/// String search result
/// </summary>
public class StringSearchResult
{
    public long Offset { get; set; }
    public string Context { get; set; } = string.Empty;
    public int MatchLength { get; set; }
}

/// <summary>
/// Binary diff result
/// </summary>
public class BinaryDiffResult
{
    public long File1Size { get; set; }
    public long File2Size { get; set; }
    public long IdenticalBytes { get; set; }
    public long DifferentBytes { get; set; }
    public double SimilarityPercent { get; set; }
    public List<long> FirstDifferences { get; set; } = new();
}

/// <summary>
/// File hash result
/// </summary>
public class FileHashResult
{
    public string MD5 { get; set; } = string.Empty;
    public string SHA1 { get; set; } = string.Empty;
    public string SHA256 { get; set; } = string.Empty;
}

/// <summary>
/// Extracted file info
/// </summary>
public class ExtractedFile
{
    public string Name { get; set; } = string.Empty;
    public string Path { get; set; } = string.Empty;
    public long Offset { get; set; }
    public long Size { get; set; }
    public string Type { get; set; } = string.Empty;
    public byte[] Data { get; set; } = Array.Empty<byte>();
}
