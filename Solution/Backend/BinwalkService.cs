using System.Security.Cryptography;
using System.Text;
using FordFirmwareEngineeringTool.Models;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for binwalk-style firmware analysis
/// </summary>
public interface IBinwalkService
{
    List<SignatureScanResult> ScanFile(byte[] data);
    EntropyAnalysis AnalyzeEntropy(byte[] data, int blockSize = 1024);
    List<ExtractedFile> ExtractFiles(byte[] data, List<SignatureScanResult>? results = null, int minSize = 0);
    List<StringSearchResult> SearchString(byte[] data, string searchTerm, bool caseSensitive = false);
    BinaryDiffResult DiffFiles(byte[] file1, byte[] file2);
    FileHashResult GetFileHash(byte[] data);
}

/// <summary>
/// Binwalk-style firmware analysis service
/// Provides signature scanning, entropy analysis, extraction, and more
/// </summary>
public class BinwalkService : IBinwalkService
{
    private readonly ILogger<BinwalkService> _logger;
    private readonly List<FileSignature> _signatures;
    
    public BinwalkService(ILogger<BinwalkService> logger)
    {
        _logger = logger;
        _signatures = InitializeSignatures();
    }
    
    /// <summary>
    /// Initialize the signature database
    /// </summary>
    private List<FileSignature> InitializeSignatures()
    {
        return new List<FileSignature>
        {
            // Archive formats
            new FileSignature
            {
                Name = "gzip",
                Magic = new byte[] { 0x1F, 0x8B },
                Description = "gzip compressed data",
                Extension = ".gz",
                Extractable = true
            },
            new FileSignature
            {
                Name = "bzip2",
                Magic = new byte[] { 0x42, 0x5A, 0x68 },
                Description = "bzip2 compressed data",
                Extension = ".bz2",
                Extractable = true
            },
            new FileSignature
            {
                Name = "xz",
                Magic = new byte[] { 0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00 },
                Description = "XZ compressed data",
                Extension = ".xz",
                Extractable = true
            },
            new FileSignature
            {
                Name = "lzma",
                Magic = new byte[] { 0x5D, 0x00, 0x00 },
                Description = "LZMA compressed data",
                Extension = ".lzma",
                Extractable = true
            },
            new FileSignature
            {
                Name = "zlib",
                Magic = new byte[] { 0x78, 0x9C },
                Description = "zlib compressed data (default)",
                Extension = ".zlib",
                Extractable = true
            },
            new FileSignature
            {
                Name = "zlib_best",
                Magic = new byte[] { 0x78, 0xDA },
                Description = "zlib compressed data (best compression)",
                Extension = ".zlib",
                Extractable = true
            },
            new FileSignature
            {
                Name = "zlib_low",
                Magic = new byte[] { 0x78, 0x01 },
                Description = "zlib compressed data (low compression)",
                Extension = ".zlib",
                Extractable = true
            },
            new FileSignature
            {
                Name = "zip",
                Magic = new byte[] { 0x50, 0x4B, 0x03, 0x04 },
                Description = "Zip archive data",
                Extension = ".zip",
                Extractable = true
            },
            new FileSignature
            {
                Name = "rar",
                Magic = new byte[] { 0x52, 0x61, 0x72, 0x21, 0x1A, 0x07 },
                Description = "RAR archive data",
                Extension = ".rar",
                Extractable = true
            },
            new FileSignature
            {
                Name = "7z",
                Magic = new byte[] { 0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C },
                Description = "7-zip archive data",
                Extension = ".7z",
                Extractable = true
            },
            new FileSignature
            {
                Name = "tar",
                Magic = Encoding.ASCII.GetBytes("ustar"),
                Offset = 257,
                Description = "POSIX tar archive",
                Extension = ".tar",
                Extractable = true
            },
            
            // Image formats
            new FileSignature
            {
                Name = "png",
                Magic = new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A },
                Description = "PNG image data",
                Extension = ".png",
                Extractable = true,
                SizeCalculator = CalculatePngSize
            },
            new FileSignature
            {
                Name = "jpeg",
                Magic = new byte[] { 0xFF, 0xD8, 0xFF },
                Description = "JPEG image data",
                Extension = ".jpg",
                Extractable = true,
                SizeCalculator = CalculateJpegSize
            },
            new FileSignature
            {
                Name = "gif87a",
                Magic = Encoding.ASCII.GetBytes("GIF87a"),
                Description = "GIF image data, version 87a",
                Extension = ".gif",
                Extractable = true
            },
            new FileSignature
            {
                Name = "gif89a",
                Magic = Encoding.ASCII.GetBytes("GIF89a"),
                Description = "GIF image data, version 89a",
                Extension = ".gif",
                Extractable = true
            },
            new FileSignature
            {
                Name = "bmp",
                Magic = new byte[] { 0x42, 0x4D },
                Description = "BMP image data",
                Extension = ".bmp",
                Extractable = true,
                SizeCalculator = CalculateBmpSize
            },
            new FileSignature
            {
                Name = "tiff_le",
                Magic = new byte[] { 0x49, 0x49, 0x2A, 0x00 },
                Description = "TIFF image data, little-endian",
                Extension = ".tiff",
                Extractable = true
            },
            new FileSignature
            {
                Name = "tiff_be",
                Magic = new byte[] { 0x4D, 0x4D, 0x00, 0x2A },
                Description = "TIFF image data, big-endian",
                Extension = ".tiff",
                Extractable = true
            },
            
            // Executable formats
            new FileSignature
            {
                Name = "elf",
                Magic = new byte[] { 0x7F, 0x45, 0x4C, 0x46 },
                Description = "ELF executable",
                Extension = ".elf",
                Extractable = true
            },
            new FileSignature
            {
                Name = "mz",
                Magic = new byte[] { 0x4D, 0x5A },
                Description = "DOS/Windows executable",
                Extension = ".exe",
                Extractable = true
            },
            new FileSignature
            {
                Name = "mach-o_32",
                Magic = new byte[] { 0xFE, 0xED, 0xFA, 0xCE },
                Description = "Mach-O 32-bit executable",
                Extension = ".macho",
                Extractable = true
            },
            new FileSignature
            {
                Name = "mach-o_64",
                Magic = new byte[] { 0xFE, 0xED, 0xFA, 0xCF },
                Description = "Mach-O 64-bit executable",
                Extension = ".macho",
                Extractable = true
            },
            
            // Filesystem formats
            new FileSignature
            {
                Name = "cramfs",
                Magic = new byte[] { 0x45, 0x3D, 0xCD, 0x28 },
                Description = "CramFS filesystem",
                Extension = ".cramfs",
                Extractable = true
            },
            new FileSignature
            {
                Name = "squashfs",
                Magic = Encoding.ASCII.GetBytes("sqsh"),
                Description = "SquashFS filesystem (big-endian)",
                Extension = ".squashfs",
                Extractable = true
            },
            new FileSignature
            {
                Name = "squashfs_le",
                Magic = Encoding.ASCII.GetBytes("hsqs"),
                Description = "SquashFS filesystem (little-endian)",
                Extension = ".squashfs",
                Extractable = true
            },
            new FileSignature
            {
                Name = "jffs2_le",
                Magic = new byte[] { 0x85, 0x19 },
                Description = "JFFS2 filesystem (little-endian)",
                Extension = ".jffs2",
                Extractable = true
            },
            new FileSignature
            {
                Name = "jffs2_be",
                Magic = new byte[] { 0x19, 0x85 },
                Description = "JFFS2 filesystem (big-endian)",
                Extension = ".jffs2",
                Extractable = true
            },
            new FileSignature
            {
                Name = "ubifs",
                Magic = new byte[] { 0x31, 0x18, 0x10, 0x06 },
                Description = "UBIFS superblock",
                Extension = ".ubifs",
                Extractable = true
            },
            new FileSignature
            {
                Name = "romfs",
                Magic = Encoding.ASCII.GetBytes("-rom1fs-"),
                Description = "RomFS filesystem",
                Extension = ".romfs",
                Extractable = true
            },
            
            // QNX formats
            new FileSignature
            {
                Name = "qnx_ifs",
                Magic = Encoding.ASCII.GetBytes("imagefs"),
                Description = "QNX IFS filesystem",
                Extension = ".ifs",
                Extractable = true
            },
            new FileSignature
            {
                Name = "qnx_startup",
                Magic = new byte[] { 0xEB, 0x7E, 0xFF, 0x00 },
                Description = "QNX startup header",
                Extension = ".startup",
                Extractable = true
            },
            
            // Automotive formats
            new FileSignature
            {
                Name = "vbf",
                Magic = Encoding.ASCII.GetBytes("vbf_version"),
                Description = "Volvo Binary Format firmware",
                Extension = ".vbf",
                Extractable = true
            },
            new FileSignature
            {
                Name = "kzb",
                Magic = new byte[] { 0x4B, 0x5A, 0x42, 0x46 }, // "KZBF"
                Description = "Kanzi Binary archive",
                Extension = ".kzb",
                Extractable = true
            },
            new FileSignature
            {
                Name = "btmp",
                Magic = Encoding.ASCII.GetBytes("BTMP"),
                Description = "Ford bitmaps.bin container",
                Extension = ".bin",
                Extractable = true
            },
            
            // Certificate/Key formats
            new FileSignature
            {
                Name = "der_cert",
                Magic = new byte[] { 0x30, 0x82 },
                Description = "DER encoded certificate/key",
                Extension = ".der",
                Extractable = true
            },
            
            // Other formats
            new FileSignature
            {
                Name = "pdf",
                Magic = Encoding.ASCII.GetBytes("%PDF"),
                Description = "PDF document",
                Extension = ".pdf",
                Extractable = true
            },
            new FileSignature
            {
                Name = "sqlite3",
                Magic = Encoding.ASCII.GetBytes("SQLite format 3"),
                Description = "SQLite 3.x database",
                Extension = ".sqlite",
                Extractable = true
            },
            new FileSignature
            {
                Name = "xml",
                Magic = Encoding.ASCII.GetBytes("<?xml"),
                Description = "XML document",
                Extension = ".xml",
                Extractable = true
            },
            new FileSignature
            {
                Name = "html",
                Magic = Encoding.ASCII.GetBytes("<!DOCTYPE html"),
                Description = "HTML document",
                Extension = ".html",
                Extractable = true
            },
            new FileSignature
            {
                Name = "shebang",
                Magic = Encoding.ASCII.GetBytes("#!"),
                Description = "Unix shell script",
                Extension = ".sh",
                Extractable = true
            }
        };
    }
    
    /// <summary>
    /// Scan file data for known signatures
    /// </summary>
    public List<SignatureScanResult> ScanFile(byte[] data)
    {
        var results = new List<SignatureScanResult>();
        
        _logger.LogDebug("Scanning {Size} bytes for signatures", data.Length);
        
        foreach (var sig in _signatures)
        {
            int searchStart = sig.Offset;
            
            while (searchStart < data.Length - sig.Magic.Length)
            {
                int pos = FindPattern(data, sig.Magic, searchStart, sig.MagicMask);
                
                if (pos < 0)
                    break;
                
                // Adjust for offset
                int actualOffset = pos - sig.Offset;
                if (actualOffset < 0)
                {
                    searchStart = pos + 1;
                    continue;
                }
                
                // Calculate size if possible
                long size = 0;
                if (sig.SizeCalculator != null)
                {
                    try
                    {
                        size = sig.SizeCalculator(data, actualOffset);
                    }
                    catch
                    {
                        size = 0;
                    }
                }
                
                results.Add(new SignatureScanResult
                {
                    Offset = actualOffset,
                    Signature = sig,
                    Size = size,
                    Description = sig.Description
                });
                
                searchStart = pos + 1;
            }
        }
        
        // Sort by offset
        results.Sort((a, b) => a.Offset.CompareTo(b.Offset));
        
        _logger.LogDebug("Found {Count} signatures", results.Count);
        
        return results;
    }
    
    /// <summary>
    /// Perform entropy analysis on file data
    /// </summary>
    public EntropyAnalysis AnalyzeEntropy(byte[] data, int blockSize = 1024)
    {
        var result = new EntropyAnalysis();
        
        int blockCount = (data.Length + blockSize - 1) / blockSize;
        double totalEntropy = 0;
        double minEntropy = double.MaxValue;
        double maxEntropy = double.MinValue;
        
        for (int i = 0; i < blockCount; i++)
        {
            int offset = i * blockSize;
            int length = Math.Min(blockSize, data.Length - offset);
            
            double entropy = CalculateEntropy(data, offset, length);
            result.EntropyValues.Add(entropy);
            
            totalEntropy += entropy;
            minEntropy = Math.Min(minEntropy, entropy);
            maxEntropy = Math.Max(maxEntropy, entropy);
            
            // Track high entropy blocks (likely encrypted/compressed)
            if (entropy > 0.9)
            {
                string desc = entropy > 0.99 ? "Encrypted/Random data" :
                              entropy > 0.95 ? "Highly compressed data" :
                              "Compressed data";
                
                result.HighEntropyBlocks.Add(new EntropyBlock
                {
                    Offset = offset,
                    Entropy = entropy,
                    Description = desc
                });
            }
        }
        
        result.BlockCount = blockCount;
        result.AverageEntropy = totalEntropy / blockCount;
        result.MinEntropy = minEntropy;
        result.MaxEntropy = maxEntropy;
        
        return result;
    }
    
    /// <summary>
    /// Extract files found during scanning
    /// </summary>
    public List<ExtractedFile> ExtractFiles(byte[] data, List<SignatureScanResult>? results = null, int minSize = 0)
    {
        results ??= ScanFile(data);
        
        var extracted = new List<ExtractedFile>();
        
        for (int i = 0; i < results.Count; i++)
        {
            var result = results[i];
            
            if (!result.Signature.Extractable)
                continue;
            
            // Determine size
            long size = result.Size;
            if (size == 0)
            {
                // Use distance to next signature or end of file
                if (i + 1 < results.Count)
                {
                    size = results[i + 1].Offset - result.Offset;
                }
                else
                {
                    size = data.Length - result.Offset;
                }
            }
            
            // Apply minimum size filter
            if (size < minSize)
                continue;
            
            // Sanity check
            if (result.Offset + size > data.Length)
            {
                size = data.Length - result.Offset;
            }
            
            if (size <= 0)
                continue;
            
            // Extract data
            byte[] fileData = new byte[size];
            Array.Copy(data, result.Offset, fileData, 0, size);
            
            string filename = $"{result.Offset:X8}_{result.Signature.Name}{result.Signature.Extension}";
            
            extracted.Add(new ExtractedFile
            {
                Name = filename,
                Path = filename,
                Offset = result.Offset,
                Size = size,
                Type = result.Signature.Name,
                Data = fileData
            });
        }
        
        return extracted;
    }
    
    /// <summary>
    /// Search for strings in binary data
    /// </summary>
    public List<StringSearchResult> SearchString(byte[] data, string searchTerm, bool caseSensitive = false)
    {
        var results = new List<StringSearchResult>();
        
        byte[] pattern = Encoding.UTF8.GetBytes(caseSensitive ? searchTerm : searchTerm.ToLower());
        byte[] searchData = caseSensitive ? data : data.Select(b => (byte)char.ToLower((char)b)).ToArray();
        
        int pos = 0;
        while (pos < searchData.Length - pattern.Length)
        {
            int found = FindPattern(searchData, pattern, pos, null);
            if (found < 0)
                break;
            
            // Get context
            int contextStart = Math.Max(0, found - 20);
            int contextEnd = Math.Min(data.Length, found + searchTerm.Length + 40);
            
            string context = GetPrintableString(data, contextStart, contextEnd - contextStart);
            
            results.Add(new StringSearchResult
            {
                Offset = found,
                Context = context,
                MatchLength = searchTerm.Length
            });
            
            pos = found + 1;
        }
        
        return results;
    }
    
    /// <summary>
    /// Compare two binary files
    /// </summary>
    public BinaryDiffResult DiffFiles(byte[] file1, byte[] file2)
    {
        var result = new BinaryDiffResult
        {
            File1Size = file1.Length,
            File2Size = file2.Length
        };
        
        long minLength = Math.Min(file1.Length, file2.Length);
        long identicalBytes = 0;
        
        for (long i = 0; i < minLength; i++)
        {
            if (file1[i] == file2[i])
            {
                identicalBytes++;
            }
            else if (result.FirstDifferences.Count < 100)
            {
                result.FirstDifferences.Add(i);
            }
        }
        
        result.IdenticalBytes = identicalBytes;
        result.DifferentBytes = minLength - identicalBytes + Math.Abs(file1.Length - file2.Length);
        
        long maxLength = Math.Max(file1.Length, file2.Length);
        result.SimilarityPercent = maxLength > 0 ? (identicalBytes * 100.0 / maxLength) : 100;
        
        return result;
    }
    
    /// <summary>
    /// Calculate file hashes
    /// </summary>
    public FileHashResult GetFileHash(byte[] data)
    {
        using var md5 = MD5.Create();
        using var sha1 = SHA1.Create();
        using var sha256 = SHA256.Create();
        
        return new FileHashResult
        {
            MD5 = BitConverter.ToString(md5.ComputeHash(data)).Replace("-", "").ToLower(),
            SHA1 = BitConverter.ToString(sha1.ComputeHash(data)).Replace("-", "").ToLower(),
            SHA256 = BitConverter.ToString(sha256.ComputeHash(data)).Replace("-", "").ToLower()
        };
    }
    
    #region Helper Methods
    
    /// <summary>
    /// Find pattern in data with optional mask
    /// </summary>
    private int FindPattern(byte[] data, byte[] pattern, int start, byte[]? mask)
    {
        for (int i = start; i <= data.Length - pattern.Length; i++)
        {
            bool match = true;
            
            for (int j = 0; j < pattern.Length && match; j++)
            {
                byte dataByte = data[i + j];
                byte patternByte = pattern[j];
                
                if (mask != null && j < mask.Length)
                {
                    dataByte &= mask[j];
                    patternByte &= mask[j];
                }
                
                if (dataByte != patternByte)
                {
                    match = false;
                }
            }
            
            if (match)
                return i;
        }
        
        return -1;
    }
    
    /// <summary>
    /// Calculate Shannon entropy for a block
    /// </summary>
    private double CalculateEntropy(byte[] data, int offset, int length)
    {
        if (length == 0) return 0;
        
        int[] counts = new int[256];
        
        for (int i = 0; i < length; i++)
        {
            counts[data[offset + i]]++;
        }
        
        double entropy = 0;
        
        for (int i = 0; i < 256; i++)
        {
            if (counts[i] > 0)
            {
                double p = (double)counts[i] / length;
                entropy -= p * Math.Log2(p);
            }
        }
        
        // Normalize to 0-1 range
        return entropy / 8.0;
    }
    
    /// <summary>
    /// Get printable string from binary data
    /// </summary>
    private string GetPrintableString(byte[] data, int offset, int length)
    {
        var sb = new StringBuilder();
        
        for (int i = 0; i < length && offset + i < data.Length; i++)
        {
            byte b = data[offset + i];
            if (b >= 32 && b < 127)
            {
                sb.Append((char)b);
            }
            else
            {
                sb.Append('.');
            }
        }
        
        return sb.ToString();
    }
    
    /// <summary>
    /// Calculate PNG file size from header
    /// </summary>
    private static long CalculatePngSize(byte[] data, int offset)
    {
        // PNG files have IEND chunk at the end
        byte[] iendMagic = { 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82 };
        
        for (int i = offset; i < data.Length - iendMagic.Length; i++)
        {
            bool match = true;
            for (int j = 0; j < iendMagic.Length && match; j++)
            {
                if (data[i + j] != iendMagic[j])
                    match = false;
            }
            
            if (match)
            {
                return i + iendMagic.Length - offset;
            }
        }
        
        return 0;
    }
    
    /// <summary>
    /// Calculate JPEG file size
    /// </summary>
    private static long CalculateJpegSize(byte[] data, int offset)
    {
        // JPEG files end with FFD9
        for (int i = offset + 2; i < data.Length - 1; i++)
        {
            if (data[i] == 0xFF && data[i + 1] == 0xD9)
            {
                return i + 2 - offset;
            }
        }
        
        return 0;
    }
    
    /// <summary>
    /// Calculate BMP file size from header
    /// </summary>
    private static long CalculateBmpSize(byte[] data, int offset)
    {
        if (offset + 6 > data.Length)
            return 0;
        
        // BMP file size is at offset 2 (little-endian)
        return BitConverter.ToUInt32(data, offset + 2);
    }
    
    #endregion
}
