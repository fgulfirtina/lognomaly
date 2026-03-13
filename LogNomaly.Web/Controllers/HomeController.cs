using LogNomaly.Web.Models;
using LogNomaly.Web.Services;
using Microsoft.AspNetCore.Mvc;

namespace LogNomaly.Web.Controllers;

public class HomeController : Controller
{
    private readonly IPythonApiService _api;
    private readonly ILogger<HomeController> _logger;

    public HomeController(IPythonApiService api, ILogger<HomeController> logger)
    {
        _api = api;
        _logger = logger;
    }

    // ── Dashboard ────────────────────────────────────────────────────
    public async Task<IActionResult> Index()
    {
        var vm = new DashboardViewModel();
        var sessionId = HttpContext.Session.GetString("SessionId");

        if (!string.IsNullOrEmpty(sessionId))
        {
            vm.SessionId = sessionId;
            vm.Stats = await _api.GetStatsAsync(sessionId);
            var results = await _api.GetResultsAsync(sessionId, 1, 10);
            if (results != null)
                vm.RecentResults = results.Results;
        }

        return View(vm);
    }

    // ── Log Upload & Analiz Sayfası ──────────────────────────────────
    public IActionResult Analyze()
    {
        return View(new AnalyzeViewModel());
    }

    [HttpPost]
    [RequestSizeLimit(52_428_800)] // 50MB
    public async Task<IActionResult> Analyze(IFormFile? logFile)
    {
        var vm = new AnalyzeViewModel();

        if (logFile == null || logFile.Length == 0)
        {
            vm.ErrorMessage = "Lütfen bir log dosyası seçin.";
            return View(vm);
        }

        // 1. Upload
        var uploadResp = await _api.UploadFileAsync(logFile);
        if (uploadResp == null)
        {
            vm.ErrorMessage = "Dosya yüklenemedi. Python API çalışıyor mu?";
            return View(vm);
        }

        // 2. Analiz
        var analyzeResp = await _api.AnalyzeFileAsync(uploadResp.FilePath, uploadResp.SessionId);
        if (analyzeResp == null)
        {
            vm.ErrorMessage = "Analiz başarısız oldu.";
            return View(vm);
        }

        // Session'a kaydet
        HttpContext.Session.SetString("SessionId", uploadResp.SessionId);

        vm.SessionId = uploadResp.SessionId;
        vm.Stats     = analyzeResp.Stats;
        vm.Results   = analyzeResp.Results;

        return View(vm);
    }

    // ── Tek Satır Analiz ─────────────────────────────────────────────
    public IActionResult SingleAnalyze()
    {
        return View(new SingleAnalyzeViewModel());
    }

    [HttpPost]
    public async Task<IActionResult> SingleAnalyze(string logLine)
    {
        var vm = new SingleAnalyzeViewModel { LogLine = logLine };

        if (string.IsNullOrWhiteSpace(logLine))
        {
            vm.ErrorMessage = "Log satırı boş olamaz.";
            return View(vm);
        }

        var result = await _api.AnalyzeSingleAsync(logLine);
        if (result == null)
        {
            vm.ErrorMessage = "Analiz başarısız. Python API çalışıyor mu?";
            return View(vm);
        }

        vm.Result = result;
        return View(vm);
    }

    // ── XAI Detay ────────────────────────────────────────────────────
    public async Task<IActionResult> Xai(string sessionId, int index)
    {
        var results = await _api.GetResultsAsync(sessionId, 1, 1000);
        if (results == null || index >= results.Results.Count)
            return RedirectToAction("Analyze");

        return View(new XaiViewModel
        {
            Result    = results.Results[index],
            SessionId = sessionId
        });
    }

    // ── API Health Check (AJAX için) ─────────────────────────────────
    [HttpGet]
    public async Task<IActionResult> ApiHealth()
    {
        var health = await _api.GetHealthAsync();
        return Json(health);
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error() => View();
}
