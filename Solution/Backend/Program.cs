using FordFirmwareEngineeringTool.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "Ford Firmware Engineering Tool API",
        Version = "v1",
        Description = "Backend API for Ford IPC custom bootsplash logo processing",
        Contact = new Microsoft.OpenApi.Models.OpenApiContact
        {
            Name = "Tester Present - Specialist Automotive Solutions",
            Url = new Uri("https://testerpresent.com.au")
        }
    });
});

// Register services
builder.Services.AddSingleton<ILzssService, LzssService>();
builder.Services.AddSingleton<ICrcService, CrcService>();
builder.Services.AddScoped<IVbfService, VbfService>();
builder.Services.AddScoped<IKzbService, KzbService>();
builder.Services.AddScoped<ITarService, TarService>();
builder.Services.AddScoped<IBitmapsService, BitmapsService>();
builder.Services.AddScoped<ISpritesheetService, SpritesheetService>();
builder.Services.AddScoped<IBinwalkService, BinwalkService>();
builder.Services.AddScoped<IDumpIfsService, DumpIfsService>();
builder.Services.AddScoped<IFirmwareProcessingService, FirmwareProcessingService>();

// Configure CORS for frontend
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader()
              .WithExposedHeaders("Content-Disposition");
    });
});

// Configure request size limits for large firmware files
builder.Services.Configure<Microsoft.AspNetCore.Http.Features.FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 100 * 1024 * 1024; // 100MB
});

builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = 100 * 1024 * 1024; // 100MB
});

// Add Application Insights for Azure monitoring
//builder.Services.AddApplicationInsightsTelemetry();

var app = builder.Build();

// Configure the HTTP request pipeline
app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Ford Firmware Engineering Tool API v1");
    c.RoutePrefix = "swagger";
});

app.UseCors("AllowAll");

// Serve static files (frontend)
app.UseDefaultFiles();
app.UseStaticFiles();

app.UseAuthorization();
app.MapControllers();

// Health check endpoint
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }));

// Fallback to index.html for SPA routing
app.MapFallbackToFile("index.html");

app.Run();
