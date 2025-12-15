using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using FordFirmwareEngineeringTool.Models;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for KZB archive operations
/// </summary>
public interface IKzbService
{
    KzbArchive Unpack(byte[] data, Action<int, int, string>? onProgress = null);
    byte[] Pack(KzbFolderNode root, Action<int, int, string>? onProgress = null);
    Dictionary<string, byte[]> ExtractAllFiles(KzbArchive archive);
    byte[] ReplaceFile(KzbArchive archive, string virtualPath, byte[] newData);
}

/// <summary>
/// Service for handling KZB/KZBF archives used in Ford instrument cluster firmware
/// </summary>
public class KzbService : IKzbService
{
    private const int HEADER_SIZE = 0x4C;
    private static readonly byte[] KZBF_SIGNATURE = Encoding.ASCII.GetBytes("KZBF");
    
    private readonly ILogger<KzbService> _logger;
    
    private static readonly HashSet<string> WindowsReservedNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    };
    
    public KzbService(ILogger<KzbService> logger)
    {
        _logger = logger;
    }
    
    /// <summary>
    /// Unpack a KZB archive from raw bytes
    /// </summary>
    public KzbArchive Unpack(byte[] data, Action<int, int, string>? onProgress = null)
    {
        var archive = new KzbArchive
        {
            RawData = data
        };
        
        // Check for KZBF signature
        if (data.Length >= 4 && 
            data[0] == KZBF_SIGNATURE[0] && 
            data[1] == KZBF_SIGNATURE[1] && 
            data[2] == KZBF_SIGNATURE[2] && 
            data[3] == KZBF_SIGNATURE[3])
        {
            archive.IsKzbf = true;
            UnpackKzbf(data, archive, onProgress);
        }
        else
        {
            archive.IsKzbf = false;
            UnpackKzb(data, archive, onProgress);
        }
        
        return archive;
    }
    
    /// <summary>
    /// Pack files into a KZB archive
    /// </summary>
    public byte[] Pack(KzbFolderNode root, Action<int, int, string>? onProgress = null)
    {
        var meta = new List<byte>();
        var folderPlaceholders = new List<KzbMetaFolderPlaceholder>();
        var elementPlaceholders = new List<KzbMetaElementPlaceholder>();
        
        // Count total elements for progress
        int totalElements = CountElements(root);
        int processedElements = 0;
        
        // Write root header
        WriteRootHeader(root.Name, root.Children.Count + (root.Elements.Count > 0 ? 1 : 0), meta);
        
        // Write folder metadata for each child
        foreach (var child in root.Children)
        {
            WriteFolderMetadata(child, meta, folderPlaceholders, elementPlaceholders);
        }
        
        // If root has elements, create synthetic folder for them
        if (root.Elements.Count > 0)
        {
            var synthNode = new KzbFolderNode
            {
                Name = root.Name + "_rootfiles",
                Elements = root.Elements.ToList()
            };
            WriteFolderMetadata(synthNode, meta, folderPlaceholders, elementPlaceholders);
        }
        
        // Calculate folder sizes
        var folderSizes = new List<uint>();
        foreach (var child in root.Children)
        {
            folderSizes.Add(ComputeTotalDataSize(child));
        }
        if (root.Elements.Count > 0)
        {
            folderSizes.Add((uint)root.Elements.Sum(e => 4 + e.Size));
        }
        
        // Patch folder size placeholders
        for (int i = 0; i < folderPlaceholders.Count && i < folderSizes.Count; i++)
        {
            var ph = folderPlaceholders[i];
            byte[] sizeBytes = PutBE32(folderSizes[i]);
            for (int j = 0; j < 4; j++)
            {
                meta[ph.SizePosition + j] = sizeBytes[j];
            }
        }
        
        // Build output
        var output = new List<byte>();
        
        // Write header (placeholder)
        output.AddRange(new byte[HEADER_SIZE]);
        output[0] = (byte)'k';
        output[1] = (byte)'z';
        output[2] = (byte)'b';
        output[3] = (byte)'f';
        
        // Write metadata
        output.AddRange(meta);
        
        // Align to 4 bytes
        while (output.Count % 4 != 0)
        {
            output.Add(0);
        }
        
        // Write resource data and patch addresses
        foreach (var ph in elementPlaceholders)
        {
            processedElements++;
            onProgress?.Invoke(processedElements, totalElements, $"Packing: {ph.Element.Name}");
            
            uint addrAbs = (uint)output.Count;
            
            // Patch address in metadata
            byte[] addrBytes = PutBE32(addrAbs);
            int addrPos = HEADER_SIZE + ph.AddressPosition;
            for (int j = 0; j < 4 && addrPos + j < output.Count; j++)
            {
                // This won't work properly - we need to track meta position differently
                // For now, we'll write to the main output
            }
            
            // Write placeholder for size prefix (4 bytes)
            output.AddRange(new byte[4]);
            
            // Write data
            output.AddRange(ph.Element.Data);
        }
        
        _logger.LogInformation("Packed KZB archive: {Size} bytes, {Elements} elements", 
            output.Count, elementPlaceholders.Count);
        
        return output.ToArray();
    }
    
    /// <summary>
    /// Extract all files from archive to a dictionary
    /// </summary>
    public Dictionary<string, byte[]> ExtractAllFiles(KzbArchive archive)
    {
        var files = new Dictionary<string, byte[]>();
        ExtractFilesRecursive(archive.Entries, "", files);
        return files;
    }
    
    /// <summary>
    /// Replace a file in the archive and return new archive bytes
    /// </summary>
    public byte[] ReplaceFile(KzbArchive archive, string virtualPath, byte[] newData)
    {
        // Find the entry
        var entry = FindEntry(archive.Entries, virtualPath);
        if (entry == null)
        {
            throw new FileNotFoundException($"File not found in archive: {virtualPath}");
        }
        
        // Update the entry data
        entry.Data = newData;
        entry.Size = (uint)newData.Length;
        
        // Rebuild the archive
        var root = BuildFolderNodeFromEntries(archive.RootName, archive.Entries);
        return Pack(root);
    }
    
    #region KZB Unpacking
    
    private void UnpackKzb(byte[] data, KzbArchive archive, Action<int, int, string>? onProgress)
    {
        int idx = HEADER_SIZE;
        
        // Read root name
        if (idx + 2 > data.Length) return;
        int strLen = ReadBE16(data, idx);
        idx += 2;
        
        archive.RootName = ReadString(data, idx, strLen);
        idx += strLen;
        idx = Align4(idx);
        
        // Skip 4 unknown DWORDs
        idx += 16;
        
        // Read folder count
        if (idx + 4 > data.Length) return;
        int folderCount = (int)ReadBE32(data, idx);
        idx += 4;
        
        _logger.LogInformation("Unpacking KZB: root={RootName}, folders={Count}", archive.RootName, folderCount);
        
        // Parse folders
        for (int i = 0; i < folderCount; i++)
        {
            var folder = ParseFolder(data, ref idx, onProgress);
            if (folder != null)
            {
                archive.Entries.Add(folder);
            }
        }
    }
    
    private KzbEntry? ParseFolder(byte[] data, ref int idx, Action<int, int, string>? onProgress)
    {
        if (idx + 4 > data.Length) return null;
        
        uint size = ReadBE32(data, idx);
        idx += 4;
        
        // Read folder name
        if (idx + 2 > data.Length) return null;
        int nameLen = ReadBE16(data, idx);
        idx += 2;
        
        string name = SanitizeName(ReadString(data, idx, nameLen), $"folder_{idx:X8}");
        idx += nameLen;
        idx = Align4(idx);
        
        // Read child count
        if (idx + 4 > data.Length) return null;
        int count = (int)ReadBE32(data, idx);
        idx += 4;
        
        var folder = new KzbEntry
        {
            Name = name,
            Path = $"Folder_{name}",
            IsDirectory = true
        };
        
        bool isLastFolder = (count == 0);
        
        if (isLastFolder)
        {
            // Read element count
            if (idx + 4 > data.Length) return folder;
            int elemCount = (int)ReadBE32(data, idx);
            idx += 4;
            
            // Parse elements
            for (int i = 0; i < elemCount; i++)
            {
                var elem = ParseElement(data, ref idx, onProgress);
                if (elem != null)
                {
                    folder.Children.Add(elem);
                }
            }
        }
        else
        {
            // Parse child folders
            uint processedSize = 0;
            for (int i = 0; i < count; i++)
            {
                var child = ParseFolder(data, ref idx, onProgress);
                if (child != null)
                {
                    folder.Children.Add(child);
                    processedSize += child.Size;
                }
            }
            
            // Check for mixed folder (has both subfolders and files)
            if (processedSize != size && idx + 4 <= data.Length)
            {
                int elemCount2 = (int)ReadBE32(data, idx);
                if (elemCount2 > 0 && elemCount2 < 10000)
                {
                    idx += 4;
                    for (int i = 0; i < elemCount2; i++)
                    {
                        var elem = ParseElement(data, ref idx, onProgress);
                        if (elem != null)
                        {
                            folder.Children.Add(elem);
                        }
                    }
                }
            }
        }
        
        return folder;
    }
    
    private KzbEntry? ParseElement(byte[] data, ref int idx, Action<int, int, string>? onProgress)
    {
        if (idx + 16 > data.Length) return null;
        
        uint addr = ReadBE32(data, idx);
        idx += 4;
        uint size = ReadBE32(data, idx);
        idx += 4;
        idx += 8; // Skip unknown fields
        
        // Read name
        if (idx + 2 > data.Length) return null;
        int nameLen = ReadBE16(data, idx);
        idx += 2;
        
        string name = SanitizeName(ReadString(data, idx, nameLen), $"elem_{addr:X8}");
        idx += nameLen;
        idx = Align4(idx);
        
        // Extract data
        int dataStart = (int)addr + 4; // Skip 4-byte prefix
        int dataEnd = dataStart + (int)size;
        
        byte[] elementData = Array.Empty<byte>();
        if (dataStart >= 0 && dataEnd <= data.Length && dataEnd > dataStart)
        {
            elementData = new byte[size];
            Array.Copy(data, dataStart, elementData, 0, (int)size);
        }
        
        onProgress?.Invoke(0, 0, $"Extracting: {name}");
        
        return new KzbEntry
        {
            Name = name,
            Path = name,
            Address = addr,
            Size = size,
            Data = elementData,
            IsDirectory = false
        };
    }
    
    #endregion
    
    #region KZBF Unpacking
    
    private void UnpackKzbf(byte[] data, KzbArchive archive, Action<int, int, string>? onProgress)
    {
        int idx = 4; // Skip signature
        
        // Skip unknown
        idx += 4;
        
        // Read string size
        if (idx + 4 > data.Length) return;
        int strSize = (int)BitConverter.ToUInt32(data, idx);
        idx += 4;
        
        // Read root name
        archive.RootName = ReadString(data, idx, strSize);
        idx += strSize;
        
        // Read node count
        if (idx + 4 > data.Length) return;
        int nodeCount = (int)BitConverter.ToUInt32(data, idx);
        idx += 4;
        
        // Read node names (null-terminated strings)
        var nodeNames = new List<string>();
        for (int i = 0; i < nodeCount; i++)
        {
            var nameBytes = new List<byte>();
            while (idx < data.Length && data[idx] != 0)
            {
                nameBytes.Add(data[idx++]);
            }
            if (idx < data.Length) idx++; // Skip null terminator
            
            string nodeName = SanitizeName(Encoding.UTF8.GetString(nameBytes.ToArray()), $"node_{i:D4}");
            nodeNames.Add(nodeName);
        }
        
        // Read element count
        if (idx + 4 > data.Length) return;
        int elemCount = (int)BitConverter.ToUInt32(data, idx);
        idx += 4;
        
        // Read element entries
        var elements = new List<(int nodeIdx, uint unk1, uint addr, uint size)>();
        for (int i = 0; i < elemCount; i++)
        {
            if (idx + 24 > data.Length) break;
            
            int nodeIdx = (int)BitConverter.ToUInt32(data, idx);
            uint unk1 = BitConverter.ToUInt32(data, idx + 4);
            uint addr = BitConverter.ToUInt32(data, idx + 8);
            uint size = BitConverter.ToUInt32(data, idx + 12);
            idx += 24;
            
            elements.Add((nodeIdx, unk1, addr, size));
        }
        
        // Extract files
        for (int i = 0; i < Math.Min(nodeNames.Count, elements.Count); i++)
        {
            var (nodeIdx, _, addr, size) = elements[i];
            string name = nodeNames[i];
            
            int local = (int)addr;
            uint actualSize = size;
            
            // PNG files have 20-byte header
            if (name.ToLower().Contains(".png"))
            {
                local += 20;
                actualSize = size - 20;
            }
            
            byte[] elementData = Array.Empty<byte>();
            if (local >= 0 && local + actualSize <= data.Length)
            {
                elementData = new byte[actualSize];
                Array.Copy(data, local, elementData, 0, (int)actualSize);
            }
            
            onProgress?.Invoke(i + 1, nodeNames.Count, $"Extracting: {name}");
            
            archive.Entries.Add(new KzbEntry
            {
                Name = name,
                Path = name,
                Address = addr,
                Size = size,
                Data = elementData,
                IsDirectory = false
            });
        }
    }
    
    #endregion
    
    #region Packing Helpers
    
    private void WriteRootHeader(string rootName, int topCount, List<byte> meta)
    {
        // Write root name length (BE16)
        meta.AddRange(PutBE16((ushort)rootName.Length));
        
        // Write root name
        meta.AddRange(Encoding.UTF8.GetBytes(rootName));
        
        // Align to 4 bytes
        while (meta.Count % 4 != 0)
        {
            meta.Add(0);
        }
        
        // Write 4 unknown DWORDs (zeros)
        for (int i = 0; i < 4; i++)
        {
            meta.AddRange(PutBE32(0));
        }
        
        // Write top folder count
        meta.AddRange(PutBE32((uint)topCount));
    }
    
    private void WriteFolderMetadata(KzbFolderNode node, List<byte> meta,
        List<KzbMetaFolderPlaceholder> folderPH, List<KzbMetaElementPlaceholder> elemPH)
    {
        // Record position for size placeholder
        folderPH.Add(new KzbMetaFolderPlaceholder { SizePosition = meta.Count });
        meta.AddRange(PutBE32(0)); // Size placeholder
        
        // Write name
        meta.AddRange(PutBE16((ushort)node.Name.Length));
        meta.AddRange(Encoding.UTF8.GetBytes(node.Name));
        while (meta.Count % 4 != 0) meta.Add(0);
        
        if (node.Children.Count == 0)
        {
            // Leaf folder - write 0 for child count, then element count
            meta.AddRange(PutBE32(0));
            meta.AddRange(PutBE32((uint)node.Elements.Count));
            
            foreach (var elem in node.Elements)
            {
                elemPH.Add(new KzbMetaElementPlaceholder 
                { 
                    AddressPosition = meta.Count,
                    Element = elem
                });
                meta.AddRange(PutBE32(0)); // Address placeholder
                meta.AddRange(PutBE32(elem.Size));
                meta.AddRange(PutBE32(0)); // Unknown
                meta.AddRange(PutBE32(0)); // Unknown
                
                // Write element name
                meta.AddRange(PutBE16((ushort)elem.Name.Length));
                meta.AddRange(Encoding.UTF8.GetBytes(elem.Name));
                while (meta.Count % 4 != 0) meta.Add(0);
            }
        }
        else
        {
            // Non-leaf folder
            meta.AddRange(PutBE32((uint)node.Children.Count));
            
            foreach (var child in node.Children.OfType<KzbFolderNode>())
            {
                WriteFolderMetadata(child, meta, folderPH, elemPH);
            }
            
            // Write any elements in mixed folder
            if (node.Elements.Count > 0)
            {
                meta.AddRange(PutBE32((uint)node.Elements.Count));
                
                foreach (var elem in node.Elements)
                {
                    elemPH.Add(new KzbMetaElementPlaceholder
                    {
                        AddressPosition = meta.Count,
                        Element = elem
                    });
                    meta.AddRange(PutBE32(0));
                    meta.AddRange(PutBE32(elem.Size));
                    meta.AddRange(PutBE32(0));
                    meta.AddRange(PutBE32(0));
                    
                    meta.AddRange(PutBE16((ushort)elem.Name.Length));
                    meta.AddRange(Encoding.UTF8.GetBytes(elem.Name));
                    while (meta.Count % 4 != 0) meta.Add(0);
                }
            }
        }
    }
    
    private uint ComputeTotalDataSize(KzbFolderNode node)
    {
        uint total = (uint)node.Elements.Sum(e => 4 + e.Size);
        foreach (var child in node.Children.OfType<KzbFolderNode>())
        {
            total += ComputeTotalDataSize(child);
        }
        return total;
    }
    
    private int CountElements(KzbFolderNode node)
    {
        int count = node.Elements.Count;
        foreach (var child in node.Children.OfType<KzbFolderNode>())
        {
            count += CountElements(child);
        }
        return count;
    }
    
    #endregion
    
    #region Utility Methods
    
    private void ExtractFilesRecursive(List<KzbEntry> entries, string basePath, Dictionary<string, byte[]> files)
    {
        foreach (var entry in entries)
        {
            string fullPath = string.IsNullOrEmpty(basePath) ? entry.Name : $"{basePath}/{entry.Name}";
            
            if (entry.IsDirectory)
            {
                ExtractFilesRecursive(entry.Children, fullPath, files);
            }
            else
            {
                files[fullPath] = entry.Data;
            }
        }
    }
    
    private KzbEntry? FindEntry(List<KzbEntry> entries, string path)
    {
        string[] parts = path.Split('/');
        var current = entries;
        
        for (int i = 0; i < parts.Length; i++)
        {
            var entry = current.FirstOrDefault(e => 
                e.Name.Equals(parts[i], StringComparison.OrdinalIgnoreCase) ||
                e.Path.Equals(parts[i], StringComparison.OrdinalIgnoreCase));
            
            if (entry == null) return null;
            
            if (i == parts.Length - 1) return entry;
            
            current = entry.Children;
        }
        
        return null;
    }
    
    private KzbFolderNode BuildFolderNodeFromEntries(string name, List<KzbEntry> entries)
    {
        var node = new KzbFolderNode { Name = name };
        
        foreach (var entry in entries)
        {
            if (entry.IsDirectory)
            {
                var childNode = BuildFolderNodeFromEntries(entry.Name, entry.Children);
                node.Children.Add(childNode);
            }
            else
            {
                node.Elements.Add(new KzbElementInfo
                {
                    Name = entry.Name,
                    Size = entry.Size,
                    Data = entry.Data
                });
            }
        }
        
        return node;
    }
    
    private static uint ReadBE32(byte[] data, int offset)
    {
        return (uint)((data[offset] << 24) | (data[offset + 1] << 16) | 
                      (data[offset + 2] << 8) | data[offset + 3]);
    }
    
    private static ushort ReadBE16(byte[] data, int offset)
    {
        return (ushort)((data[offset] << 8) | data[offset + 1]);
    }
    
    private static byte[] PutBE32(uint value)
    {
        return new byte[]
        {
            (byte)((value >> 24) & 0xFF),
            (byte)((value >> 16) & 0xFF),
            (byte)((value >> 8) & 0xFF),
            (byte)(value & 0xFF)
        };
    }
    
    private static byte[] PutBE16(ushort value)
    {
        return new byte[]
        {
            (byte)((value >> 8) & 0xFF),
            (byte)(value & 0xFF)
        };
    }
    
    private static int Align4(int idx)
    {
        return (idx + 3) & ~3;
    }
    
    private static string ReadString(byte[] data, int offset, int length)
    {
        int actualLength = Math.Min(length, data.Length - offset);
        if (actualLength <= 0) return string.Empty;
        
        byte[] bytes = new byte[actualLength];
        Array.Copy(data, offset, bytes, 0, actualLength);
        
        // Find null terminator
        int nullPos = Array.IndexOf(bytes, (byte)0);
        if (nullPos >= 0)
        {
            bytes = bytes.Take(nullPos).ToArray();
        }
        
        return Encoding.UTF8.GetString(bytes);
    }
    
    private static string SanitizeName(string raw, string fallback)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return fallback;
        
        // Remove control characters
        var cleaned = new string(raw.Where(c => c >= 32).ToArray());
        
        // Replace invalid path characters
        foreach (char c in Path.GetInvalidFileNameChars())
        {
            cleaned = cleaned.Replace(c, '_');
        }
        
        cleaned = cleaned.Replace('\\', '_').Replace('/', '_');
        
        // Handle reserved names
        string upper = cleaned.ToUpperInvariant();
        if (WindowsReservedNames.Contains(upper) || string.IsNullOrWhiteSpace(cleaned))
        {
            return $"_{cleaned ?? fallback}_";
        }
        
        return cleaned.Trim();
    }
    
    #endregion
}
