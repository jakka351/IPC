namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for LZSS compression/decompression services
/// </summary>
public interface ILzssService
{
    byte[] Compress(byte[] data, Action<double>? onProgress = null);
    byte[] Decompress(byte[] data, int expectedSize = 0);
}

/// <summary>
/// LZSS compression service - faithful port of the Ford/IDA-style LZSS variant
/// Window = 1024 (10-bit offset), lookahead up to 17 (emit len-2 in 4 bits)
/// Bitstream: [flag bit][(if 0) 10-bit pos + 4-bit (len-2)] | [if 1: 8-bit literal]
/// </summary>
public class LzssService : ILzssService
{
    private const int WINDOW_SIZE = 1024;
    private const int MAX_MATCH_LENGTH = 17;
    private const int MIN_MATCH_LENGTH = 2;
    private const int LOOKAHEAD_SIZE = 17;
    
    private class TreeNode
    {
        public int Parent { get; set; }
        public int SmallChild { get; set; }
        public int LargeChild { get; set; }
    }
    
    private class LzssContext
    {
        public List<byte> CompressedData { get; } = new();
        public int OutBit { get; set; } = 0x80;
        public int OutLen { get; set; }
        public byte[] LzssWindow { get; } = new byte[WINDOW_SIZE];
        public int MatchLength { get; set; }
        public TreeNode[] Tree { get; } = new TreeNode[WINDOW_SIZE + 1];
        public int CurrentByte { get; set; }
        
        public LzssContext()
        {
            for (int i = 0; i <= WINDOW_SIZE; i++)
            {
                Tree[i] = new TreeNode();
            }
        }
    }
    
    /// <summary>
    /// Compress data using LZSS algorithm
    /// </summary>
    public byte[] Compress(byte[] data, Action<double>? onProgress = null)
    {
        if (data == null || data.Length == 0)
            return Array.Empty<byte>();
        
        var ctx = new LzssContext();
        int inputLength = data.Length;
        
        // Initialize state
        int winPos = 1;
        int replCnt = 0;
        int matchPos = 0;
        bool eosReached = false;
        int inPtr = 0;
        
        // Clear window and tree
        Array.Clear(ctx.LzssWindow, 0, WINDOW_SIZE);
        for (int i = 0; i <= WINDOW_SIZE; i++)
        {
            ctx.Tree[i].Parent = 0;
            ctx.Tree[i].SmallChild = 0;
            ctx.Tree[i].LargeChild = 0;
        }
        
        // Preload lookahead buffer
        int byte2Win = 0;
        while (byte2Win <= 0x10 && !eosReached)
        {
            if (inPtr < inputLength)
            {
                int idx = (winPos + byte2Win) & 0x3FF;
                ctx.LzssWindow[idx] = data[inPtr++];
                byte2Win++;
            }
            else
            {
                eosReached = true;
            }
        }
        
        // Initialize tree with first position
        InitTree(winPos & 0x3FF, ctx);
        
        // Main compression loop
        while (byte2Win > 0)
        {
            // Report progress
            if (onProgress != null && inPtr % 1000 == 0)
            {
                onProgress(Math.Min(0.95, (double)inPtr / inputLength));
            }
            
            // Clamp match length to available data
            if (ctx.MatchLength > byte2Win)
                ctx.MatchLength = byte2Win;
            
            // Find best match at current position
            (ctx.MatchLength, matchPos) = AddNode(winPos & 0x3FF, ctx);
            
            if (ctx.MatchLength > 1)
            {
                // Output match: flag 0, 10-bit position, 4-bit (length - 2)
                OutputBits(0, 1, ctx);
                OutputBits(matchPos & 0x3FF, 10, ctx);
                OutputBits((ctx.MatchLength - 2) & 0x0F, 4, ctx);
                replCnt = ctx.MatchLength;
            }
            else
            {
                // Output literal: flag 1, 8-bit byte
                replCnt = 1;
                OutputBits(1, 1, ctx);
                OutputBits(ctx.LzssWindow[winPos & 0x3FF], 8, ctx);
            }
            
            // Slide window
            for (int i = 0; i < replCnt; i++)
            {
                // Delete node at current position
                DeleteNode(winPos & 0x3FF, ctx);
                
                if (inPtr < inputLength)
                {
                    // Load next byte into lookahead
                    int storePos = ((winPos & 0xFFFF) + 0x10) & 0x3FF;
                    ctx.LzssWindow[storePos] = data[inPtr++];
                }
                else
                {
                    // Shrink lookahead
                    byte2Win--;
                }
                
                // Advance window position
                winPos = ((winPos & 0xFFFF) + 1) & 0x3FF;
                if (winPos == 0) winPos = 1; // Avoid position 0
            }
        }
        
        // Output terminator: flag 0, 10 zero bits
        OutputBits(0, 1, ctx);
        OutputBits(0, 10, ctx);
        
        // Append trailing zero byte
        ctx.CompressedData.Add(0);
        
        onProgress?.Invoke(1.0);
        
        return ctx.CompressedData.ToArray();
    }
    
    /// <summary>
    /// Decompress LZSS compressed data
    /// </summary>
    public byte[] Decompress(byte[] data, int expectedSize = 0)
    {
        if (data == null || data.Length == 0)
            return Array.Empty<byte>();
        
        var output = new List<byte>(expectedSize > 0 ? expectedSize : data.Length * 2);
        var window = new byte[WINDOW_SIZE];
        int windowPos = 1;
        int bitPos = 0;
        int bytePos = 0;
        
        int ReadBit()
        {
            if (bytePos >= data.Length) return 0;
            int bit = (data[bytePos] >> (7 - bitPos)) & 1;
            bitPos++;
            if (bitPos >= 8)
            {
                bitPos = 0;
                bytePos++;
            }
            return bit;
        }
        
        int ReadBits(int count)
        {
            int value = 0;
            for (int i = 0; i < count; i++)
            {
                value = (value << 1) | ReadBit();
            }
            return value;
        }
        
        while (bytePos < data.Length)
        {
            int flag = ReadBit();
            
            if (flag == 1)
            {
                // Literal byte
                byte literal = (byte)ReadBits(8);
                output.Add(literal);
                window[windowPos] = literal;
                windowPos = (windowPos + 1) & 0x3FF;
                if (windowPos == 0) windowPos = 1;
            }
            else
            {
                // Match reference
                int pos = ReadBits(10);
                
                if (pos == 0)
                {
                    // End of stream
                    break;
                }
                
                int length = ReadBits(4) + 2;
                
                for (int i = 0; i < length; i++)
                {
                    byte b = window[(pos + i) & 0x3FF];
                    output.Add(b);
                    window[windowPos] = b;
                    windowPos = (windowPos + 1) & 0x3FF;
                    if (windowPos == 0) windowPos = 1;
                }
            }
        }
        
        return output.ToArray();
    }
    
    #region Tree Operations
    
    private void InitTree(int rootChild, LzssContext ctx)
    {
        ctx.Tree[WINDOW_SIZE].Parent = 0;
        ctx.Tree[WINDOW_SIZE].SmallChild = 0;
        ctx.Tree[WINDOW_SIZE].LargeChild = rootChild;
        ctx.Tree[rootChild].Parent = WINDOW_SIZE;
        ctx.Tree[rootChild].LargeChild = 0;
        ctx.Tree[rootChild].SmallChild = 0;
    }
    
    private void ContractNode(int oldNode, int newNode, LzssContext ctx)
    {
        ctx.Tree[newNode].Parent = ctx.Tree[oldNode].Parent;
        if (ctx.Tree[ctx.Tree[oldNode].Parent].LargeChild == oldNode)
            ctx.Tree[ctx.Tree[oldNode].Parent].LargeChild = newNode;
        else
            ctx.Tree[ctx.Tree[oldNode].Parent].SmallChild = newNode;
        ctx.Tree[oldNode].Parent = 0;
        ctx.Tree[oldNode].SmallChild = 0;
        ctx.Tree[oldNode].LargeChild = 0;
    }
    
    private void ReplaceNode(int oldNode, int newNode, LzssContext ctx)
    {
        int parent = ctx.Tree[oldNode].Parent;
        if (ctx.Tree[parent].SmallChild == oldNode)
            ctx.Tree[parent].SmallChild = newNode;
        else
            ctx.Tree[parent].LargeChild = newNode;
        
        ctx.Tree[newNode].Parent = ctx.Tree[oldNode].Parent;
        ctx.Tree[newNode].SmallChild = ctx.Tree[oldNode].SmallChild;
        ctx.Tree[newNode].LargeChild = ctx.Tree[oldNode].LargeChild;
        
        int sc = ctx.Tree[newNode].SmallChild;
        int lc = ctx.Tree[newNode].LargeChild;
        if (sc > 0) ctx.Tree[sc].Parent = newNode;
        if (lc > 0) ctx.Tree[lc].Parent = newNode;
        
        ctx.Tree[oldNode].Parent = 0;
        ctx.Tree[oldNode].SmallChild = 0;
        ctx.Tree[oldNode].LargeChild = 0;
    }
    
    private int FindNextNode(int node, LzssContext ctx)
    {
        int next = ctx.Tree[node].SmallChild;
        while (ctx.Tree[next].LargeChild > 0)
        {
            next = ctx.Tree[next].LargeChild;
        }
        return next;
    }
    
    private void DeleteNode(int node, LzssContext ctx)
    {
        if (node == 0 || node >= WINDOW_SIZE) return;
        
        if (ctx.Tree[node].LargeChild > 0)
        {
            if (ctx.Tree[node].SmallChild > 0)
            {
                int replNode = FindNextNode(node, ctx);
                ContractNode(replNode, ctx.Tree[replNode].SmallChild, ctx);
                ReplaceNode(node, replNode, ctx);
            }
            else
            {
                ContractNode(node, ctx.Tree[node].LargeChild, ctx);
            }
        }
        else
        {
            ContractNode(node, ctx.Tree[node].SmallChild, ctx);
        }
    }
    
    private (int matchLen, int matchPos) AddNode(int newNode, LzssContext ctx)
    {
        if (newNode == 0)
        {
            return (0, 0);
        }
        
        int matchPos = 0;
        int matchLen = 0;
        int testNode = ctx.Tree[WINDOW_SIZE].LargeChild;
        
        while (true)
        {
            int testLen = 0;
            int delta = 0;
            
            // Compare strings
            while (testLen <= 0x10 && delta == 0)
            {
                int idx1 = (newNode + testLen) & 0x3FF;
                int idx2 = (testNode + testLen) & 0x3FF;
                delta = ctx.LzssWindow[idx1] - ctx.LzssWindow[idx2];
                testLen++;
            }
            
            if (delta != 0)
                testLen--;
            
            if (testLen >= matchLen)
            {
                matchLen = testLen;
                matchPos = testNode;
                
                if (testLen > 0x10)
                {
                    ReplaceNode(testNode, newNode, ctx);
                    return (testLen, matchPos);
                }
            }
            
            // Navigate tree based on comparison
            if (delta < 0)
            {
                if (ctx.Tree[testNode].SmallChild == 0)
                {
                    ctx.Tree[testNode].SmallChild = newNode;
                    ctx.Tree[newNode].Parent = testNode;
                    ctx.Tree[newNode].LargeChild = 0;
                    ctx.Tree[newNode].SmallChild = 0;
                    return (matchLen, matchPos);
                }
                testNode = ctx.Tree[testNode].SmallChild;
            }
            else
            {
                if (ctx.Tree[testNode].LargeChild == 0)
                {
                    ctx.Tree[testNode].LargeChild = newNode;
                    ctx.Tree[newNode].Parent = testNode;
                    ctx.Tree[newNode].LargeChild = 0;
                    ctx.Tree[newNode].SmallChild = 0;
                    return (matchLen, matchPos);
                }
                testNode = ctx.Tree[testNode].LargeChild;
            }
        }
    }
    
    #endregion
    
    #region Bit Output
    
    private void OutputBits(int bits, int numBits, LzssContext ctx)
    {
        int bitValue = numBits > 0 ? 1 << (numBits - 1) : 0;
        
        for (int i = 0; i < numBits; i++)
        {
            if (ctx.OutBit == 0x80)
            {
                ctx.CompressedData.Add(0);
                ctx.CurrentByte = ctx.CompressedData.Count - 1;
                ctx.OutLen++;
            }
            
            if ((bits & bitValue) != 0)
            {
                ctx.CompressedData[ctx.CurrentByte] |= (byte)ctx.OutBit;
            }
            
            if (ctx.OutBit == 0x01)
            {
                ctx.OutBit = 0x80;
            }
            else
            {
                ctx.OutBit >>= 1;
            }
            
            bitValue >>= 1;
        }
    }
    
    #endregion
}
