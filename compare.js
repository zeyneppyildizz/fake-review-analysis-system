//SAYFA YÜKLENDİĞİNDE HAFIZAYI KONTROL ET (F5 KALKANI)

document.addEventListener("DOMContentLoaded", () => {
    const kayitliVeri = localStorage.getItem("sonKiyaslamaVerisi");
    
    if (kayitliVeri) {
        try {
            const data = JSON.parse(kayitliVeri);
            
            // Essential veriler var mı kontrol et
            if (!data.urun1?.ozet || !data.urun2?.ozet) {
                console.log("[RADAR AI] Eksik veri, hafıza temizleniyor...");
                localStorage.removeItem("sonKiyaslamaVerisi");
                return;
            }
            
            console.log("[RADAR AI] F5 Koruması: Veriler başarıyla geri yüklendi.");
            if (data.urun1_url) document.getElementById("url1").value = data.urun1_url;
            if (data.urun2_url) document.getElementById("url2").value = data.urun2_url;
            
            ekranaCiz(data);
        } catch (e) {
            console.error("[RADAR AI] Önbellek yüklenirken hata:", e);
            localStorage.removeItem("sonKiyaslamaVerisi");
        }
    }
});

let chartPie1 = null, chartPie2 = null, chartDist1 = null, chartDist2 = null; 

// KARŞILAŞTIR BUTONU 

document.addEventListener("DOMContentLoaded", () => {
    const kiyaslaButonu = document.getElementById("btnKiyasla");
    if (kiyaslaButonu) {
        kiyaslaButonu.addEventListener("click", async () => {
            const url1 = document.getElementById("url1").value.trim();
            const url2 = document.getElementById("url2").value.trim();
            const username = sessionStorage.getItem("username") || "demo_user";

            if (!url1 || !url2) return alert("Lütfen iki ürün linkini de girin!");

            document.getElementById("loading").style.display = "block";
            document.getElementById("resultsPanel").style.display = "none";
            localStorage.removeItem("sonKiyaslamaVerisi"); 

            try {
                const response = await fetch("http://127.0.0.1:8000/api/kiyasla", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url1, url2, username })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "Analiz hatası.");

                data.urun1_url = url1;
                data.urun2_url = url2;
                localStorage.setItem("sonKiyaslamaVerisi", JSON.stringify(data));

                document.getElementById("loading").style.display = "none";
                ekranaCiz(data);
            } catch (error) {
                document.getElementById("loading").style.display = "none";
                alert("API Hatası: " + error.message);
            }
        });
    }
});

// GRAFİK VE UI ÇİZİM MOTORU (İNDEX İLE AYNI TASARIM)
function ekranaCiz(data) {
    document.getElementById("resultsPanel").style.display = "flex";
    document.getElementById("dssDecisionText").innerText = data.dss_karar || "Karar verilemedi.";

    // DAĞILIM VERİLERİNİ HESAPLA (script.js ile aynı mantık)
    const hesaplaDagilim = (yorumlar) => {
        const dist = [0, 0, 0, 0, 0];
        if (yorumlar && Array.isArray(yorumlar)) {
            yorumlar.forEach(item => {
                let score = parseFloat(item.guven_skoru);
                if (score <= 1) score = score * 100;
                let index = Math.floor(score / 20);
                if (index > 4) index = 4;
                if (index < 0) index = 0;
                if (item.karar === 'GERÇEK') dist[index]++;
                else if (item.karar === 'SAHTE') dist[index]++;
            });
        }
        return dist;
    };

    // Metrikleri Güncelle
    const r1 = data.urun1?.ozet?.sahtelik_orani ?? 0;
    document.getElementById("u1-risk").innerText = "%" + r1;
    document.getElementById("u1-gercek").innerText = data.urun1?.ozet?.gercek_yorum_sayisi ?? 0;
    document.getElementById("u1-sahte").innerText = data.urun1?.ozet?.sahte_yorum_sayisi ?? 0;
    document.getElementById("u1-progress").style.width = r1 + "%";

    const r2 = data.urun2?.ozet?.sahtelik_orani ?? 0;
    document.getElementById("u2-risk").innerText = "%" + r2;
    document.getElementById("u2-gercek").innerText = data.urun2?.ozet?.gercek_yorum_sayisi ?? 0;
    document.getElementById("u2-sahte").innerText = data.urun2?.ozet?.sahte_yorum_sayisi ?? 0;
    document.getElementById("u2-progress").style.width = r2 + "%";

    [chartPie1, chartPie2, chartDist1, chartDist2].forEach(c => c?.destroy());

    // Yeni Kurumsal SaaS Teması Grafikleri İçin Global Ayarlar
    Chart.defaults.color = '#a1a1aa';
    Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

    // PASTA GRAFİKLERİ
    chartPie1 = new Chart(document.getElementById('pieChart1'), {
        type: 'doughnut',
        data: {
            labels: ['Organik', 'Sentetik'],
            datasets: [{
                data: [data.urun1?.ozet?.gercek_yorum_sayisi ?? 0, data.urun1?.ozet?.sahte_yorum_sayisi ?? 0],
                backgroundColor: ['#16a34a', '#dc2626'], // Tok, kurumsal yeşil ve kırmızı
                borderColor: ['#14532d', '#7f1d1d'], // Koyu, net çerçeve sınırları
                borderWidth: 2
            }]
        },
        options: { cutout: '75%', plugins: { legend: { position: 'bottom' } }, responsive: true, maintainAspectRatio: false }
    });

    chartPie2 = new Chart(document.getElementById('pieChart2'), {
        type: 'doughnut',
        data: {
            labels: ['Organik', 'Sentetik'],
            datasets: [{
                data: [data.urun2?.ozet?.gercek_yorum_sayisi ?? 0, data.urun2?.ozet?.sahte_yorum_sayisi ?? 0],
                backgroundColor: ['#16a34a', '#dc2626'],
                borderColor: ['#14532d', '#7f1d1d'],
                borderWidth: 2
            }]
        },
        options: { cutout: '75%', plugins: { legend: { position: 'bottom' } }, responsive: true, maintainAspectRatio: false }
    });

    // BAR GRAFİKLERİ 
    const drawBar = (canvasId, dataGercek, dataSahte) => {
        return new Chart(document.getElementById(canvasId), {
            type: 'bar',
            data: {
                labels: ['%0-20', '%20-40', '%40-60', '%60-80', '%80-100'],
                datasets: [
                    { label: 'Organik', data: dataGercek, backgroundColor: '#16a34a', borderColor: '#14532d', borderWidth: 1, borderRadius: 4, barPercentage: 0.8 },
                    { label: 'Sentetik', data: dataSahte, backgroundColor: '#dc2626', borderColor: '#7f1d1d', borderWidth: 1, borderRadius: 4, barPercentage: 0.8 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { labels: { usePointStyle: true, padding: 10 } } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#27272a' }, ticks: { stepSize: 1 } },
                    x: { grid: { display: false } }
                }
            }
        });
    };

    const gercekDist1 = [0, 0, 0, 0, 0], sahteDist1 = [0, 0, 0, 0, 0];
    const gercekDist2 = [0, 0, 0, 0, 0], sahteDist2 = [0, 0, 0, 0, 0];

    // Ürün 1 dağılımı
    if (data.urun1?.yorumlar) {
        data.urun1.yorumlar.forEach(item => {
            let score = parseFloat(item.guven_skoru);
            if (score <= 1) score = score * 100;
            let index = Math.floor(score / 20);
            if (index > 4) index = 4;
            if (index < 0) index = 0;
            if (item.karar === 'GERÇEK') gercekDist1[index]++;
            else if (item.karar === 'SAHTE') sahteDist1[index]++;
        });
    }

    // Ürün 2 dağılımı
    if (data.urun2?.yorumlar) {
        data.urun2.yorumlar.forEach(item => {
            let score = parseFloat(item.guven_skoru);
            if (score <= 1) score = score * 100;
            let index = Math.floor(score / 20);
            if (index > 4) index = 4;
            if (index < 0) index = 0;
            if (item.karar === 'GERÇEK') gercekDist2[index]++;
            else if (item.karar === 'SAHTE') sahteDist2[index]++;
        });
    }

    chartDist1 = drawBar('distChart1', gercekDist1, sahteDist1);
    chartDist2 = drawBar('distChart2', gercekDist2, sahteDist2);
}