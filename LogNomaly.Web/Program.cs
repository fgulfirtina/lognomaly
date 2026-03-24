using LogNomaly.Web.Data;
using LogNomaly.Web.Services;
using LogNomaly.Web.Services.Contracts;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// PostgreSQL Veritabaný Baðlantýsý
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// Cookie Authentication
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/Auth/Login"; // Giriþ yapmayanlarý buraya atar
        options.AccessDeniedPath = "/Auth/AccessDenied"; // Yetkisi yetmeyenleri buraya atar
        options.ExpireTimeSpan = TimeSpan.FromHours(8); // 8 saat sonra otomatik çýkýþ
    });

builder.Services.AddControllersWithViews();
builder.Services.AddHttpClient<IPythonApiService, PythonApiService>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["PythonApi:BaseUrl"] ?? "http://localhost:5000");
    client.Timeout = TimeSpan.FromSeconds(120);
});
builder.Services.AddSession(options =>
{
    options.IdleTimeout = TimeSpan.FromMinutes(30);
    options.Cookie.HttpOnly = true;
});
// Feedback servisini sisteme tanýtýyoruz
builder.Services.AddScoped<IFeedbackService, FeedbackService>();

var app = builder.Build();

// Hata Yönetimi
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Home/Error");
    app.UseHsts();
}

// HTTPS ve Statik Dosyalar
app.UseHttpsRedirection();
app.UseStaticFiles();

// Routing (Yönlendirme)
app.UseRouting();

// Session
app.UseSession();

// Kimlik Doðrulama ve Yetkilendirme (Sýrasýyla önce kimlik, sonra yetki)
app.UseAuthentication();
app.UseAuthorization();

// Endpoint'ler
app.MapControllerRoute(
    name: "default",
    pattern: "{controller=Home}/{action=Index}/{id?}");

app.Run();
