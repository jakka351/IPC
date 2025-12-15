using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;
using SixLabors.ImageSharp.Drawing.Processing;

namespace FordFirmwareEngineeringTool.Services;

/// <summary>
/// Interface for spritesheet operations
/// </summary>
public interface ISpritesheetService
{
    byte[] ApplyLogoToSpritesheet(byte[] spritesheetData, byte[] logoData, SpritesheetOptions? options = null);
    byte[] ApplyLogoToAllSpritesheets(IEnumerable<byte[]> spritesheets, byte[] logoData, SpritesheetOptions? options = null);
    bool IsSpritesheet(byte[] imageData, int expectedRows = 4, int expectedCols = 4);
}

/// <summary>
/// Options for spritesheet logo application
/// </summary>
public class SpritesheetOptions
{
    public int Rows { get; set; } = 4;
    public int Cols { get; set; } = 4;
    public float MaxRatio { get; set; } = 0.45f;
    public int PaddingPx { get; set; } = 0;
    public bool PreserveAlpha { get; set; } = true;
}

/// <summary>
/// Service for applying logos to spritesheets used in Ford IPC bootsplash animations
/// </summary>
public class SpritesheetService : ISpritesheetService
{
    private readonly ILogger<SpritesheetService> _logger;
    
    public SpritesheetService(ILogger<SpritesheetService> logger)
    {
        _logger = logger;
    }
    
    /// <summary>
    /// Apply a logo to the center of each tile in a spritesheet
    /// </summary>
    public byte[] ApplyLogoToSpritesheet(byte[] spritesheetData, byte[] logoData, SpritesheetOptions? options = null)
    {
        options ??= new SpritesheetOptions();
        
        using var sheetImage = Image.Load<Rgba32>(spritesheetData);
        using var logoImage = Image.Load<Rgba32>(logoData);
        
        int sheetWidth = sheetImage.Width;
        int sheetHeight = sheetImage.Height;
        
        // Validate dimensions
        if (sheetWidth % options.Cols != 0 || sheetHeight % options.Rows != 0)
        {
            throw new ArgumentException(
                $"Sheet size {sheetWidth}x{sheetHeight} not divisible by grid {options.Cols}x{options.Rows}");
        }
        
        int tileWidth = sheetWidth / options.Cols;
        int tileHeight = sheetHeight / options.Rows;
        
        _logger.LogDebug("Processing spritesheet: {Width}x{Height}, tiles: {TileW}x{TileH}", 
            sheetWidth, sheetHeight, tileWidth, tileHeight);
        
        // Resize logo to fit within tiles
        var resizedLogo = ResizeLogoToFit(logoImage, tileWidth, tileHeight, options.MaxRatio, options.PaddingPx);
        
        int logoWidth = resizedLogo.Width;
        int logoHeight = resizedLogo.Height;
        
        _logger.LogDebug("Logo resized to: {Width}x{Height}", logoWidth, logoHeight);
        
        // Apply logo to each tile
        for (int row = 0; row < options.Rows; row++)
        {
            for (int col = 0; col < options.Cols; col++)
            {
                int tileX = col * tileWidth;
                int tileY = row * tileHeight;
                
                // Calculate center position
                int centerX = tileX + (tileWidth / 2);
                int centerY = tileY + (tileHeight / 2);
                
                // Calculate paste position (top-left of logo)
                int pasteX = centerX - (logoWidth / 2);
                int pasteY = centerY - (logoHeight / 2);
                
                // Composite the logo onto the spritesheet
                CompositeLogoAtPosition(sheetImage, resizedLogo, pasteX, pasteY);
            }
        }
        
        // Encode to PNG
        using var outputStream = new MemoryStream();
        sheetImage.SaveAsPng(outputStream);
        
        _logger.LogInformation("Applied logo to spritesheet: {Rows}x{Cols} grid", options.Rows, options.Cols);
        
        return outputStream.ToArray();
    }
    
    /// <summary>
    /// Apply logo to multiple spritesheets
    /// </summary>
    public byte[] ApplyLogoToAllSpritesheets(IEnumerable<byte[]> spritesheets, byte[] logoData, SpritesheetOptions? options = null)
    {
        var results = new List<byte[]>();
        
        foreach (var sheet in spritesheets)
        {
            try
            {
                var modified = ApplyLogoToSpritesheet(sheet, logoData, options);
                results.Add(modified);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to process one spritesheet, skipping");
            }
        }
        
        // Return first result (caller should handle multiple)
        return results.FirstOrDefault() ?? Array.Empty<byte>();
    }
    
    /// <summary>
    /// Check if an image appears to be a spritesheet
    /// </summary>
    public bool IsSpritesheet(byte[] imageData, int expectedRows = 4, int expectedCols = 4)
    {
        try
        {
            using var image = Image.Load(imageData);
            
            // Check if dimensions are divisible by expected grid
            return image.Width % expectedCols == 0 && 
                   image.Height % expectedRows == 0 &&
                   image.Width >= expectedCols * 10 && // At least 10px per tile
                   image.Height >= expectedRows * 10;
        }
        catch
        {
            return false;
        }
    }
    
    #region Private Methods
    
    private Image<Rgba32> ResizeLogoToFit(Image<Rgba32> logo, int tileWidth, int tileHeight, float maxRatio, int paddingPx)
    {
        // Calculate max dimensions for logo
        int maxSide = (int)(maxRatio * Math.Min(tileWidth, tileHeight));
        int maxWidth = Math.Max(1, maxSide - 2 * paddingPx);
        int maxHeight = Math.Max(1, maxSide - 2 * paddingPx);
        
        int logoWidth = logo.Width;
        int logoHeight = logo.Height;
        
        // Calculate scale to fit within bounds
        float scaleX = (float)maxWidth / logoWidth;
        float scaleY = (float)maxHeight / logoHeight;
        float scale = Math.Min(Math.Min(scaleX, scaleY), 1.0f); // Don't upscale
        
        int newWidth = Math.Max(1, (int)(logoWidth * scale));
        int newHeight = Math.Max(1, (int)(logoHeight * scale));
        
        if (newWidth == logoWidth && newHeight == logoHeight)
        {
            return logo.Clone();
        }
        
        // Resize the logo
        var resized = logo.Clone(ctx => ctx.Resize(newWidth, newHeight, KnownResamplers.Lanczos3));
        
        return resized;
    }
    
    private void CompositeLogoAtPosition(Image<Rgba32> target, Image<Rgba32> source, int x, int y)
    {
        // Use ImageSharp's built-in compositing
        target.Mutate(ctx =>
        {
            ctx.DrawImage(source, new Point(x, y), 1f);
        });
    }
    
    #endregion
}
