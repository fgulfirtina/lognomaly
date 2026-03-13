// LogNomaly — Frontend JS

// API sağlık kontrolü
(function checkApiHealth() {
    fetch('/Home/ApiHealth')
        .then(r => r.json())
        .then(data => {
            var dot  = document.querySelector('.status-dot');
            var text = document.querySelector('.status-text');
            if (!dot || !text) return;
            if (data && data.models_loaded) {
                dot.className  = 'status-dot ok';
                text.textContent = 'API · Modeller Hazır';
            } else {
                dot.className  = 'status-dot error';
                text.textContent = 'API · Model Yüklenmedi';
            }
        })
        .catch(() => {
            var dot  = document.querySelector('.status-dot');
            var text = document.querySelector('.status-text');
            if (!dot || !text) return;
            dot.className  = 'status-dot error';
            text.textContent = 'API · Bağlanamıyor';
        });
})();
