// ==========================================
// 1. GENEL AYARLAR, YÖNLENDİRME (ROUTING) VE ANA SAYFA (INDEX) İŞLEMLERİ
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    
    let currentPath = window.location.pathname.split("/").pop();
    if (currentPath === "") currentPath = "index.html"; 

    const navLinks = document.querySelectorAll(".nav-link-custom");
    navLinks.forEach(link => {
        if (link.classList.contains("text-danger")) return;

        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    // 2. GÜVENLİK VE YÖNLENDİRME (ROUTING)
    const isLoggedIn = sessionStorage.getItem("isLoggedIn") || localStorage.getItem("isLoggedIn");
    const currentPathLower = window.location.pathname.toLowerCase();
    
    const isAuthPage = currentPathLower.includes("login.html") || currentPathLower.includes("register.html") || currentPathLower.includes("forgotpassword.html");

    console.log("[AUTH CHECK] isLoggedIn=" + isLoggedIn + ", currentPath=" + currentPathLower);

    // Giriş yapılmamışsa ve auth sayfasında değilse login'e at
    if (isLoggedIn !== "true" && !isAuthPage) {
        console.log("[AUTH CHECK] Giriş yapılmamış, login'e yönlendiriliyor");
        window.location.href = "login.html";
    } 
    // Giriş yapılmışsa ve auth sayfasındaysa index'e at
    else if (isLoggedIn === "true" && isAuthPage) {
        console.log("[AUTH CHECK] Zaten giriş yapılmış, index'e yönlendiriliyor");
        window.location.href = "index.html";
    } else {
        console.log("[AUTH CHECK] Auth kontrol tamam");
    }

    // Profil sayfasındaysa verileri çek
    if (currentPathLower.includes("profile.html")) {
        loadUserProfile();       
    }
    
    // Ana sayfadaysa eski analiz verisini yükle
    if (currentPathLower.includes("index.html") || currentPathLower === "/" || currentPathLower.endsWith("/")) {
        if(typeof restoreDashboard === "function") restoreDashboard();
    }

    // 3. ANALİZ BUTONU VE API İSTEĞİ
    const btnAnaliz = document.getElementById('btnAnaliz');
    if (btnAnaliz) {
        btnAnaliz.addEventListener('click', async (e) => {
            
            e.preventDefault();
            e.stopPropagation();
            
            const url = document.getElementById('amazonUrl').value;
            if(!url) return alert("Amazon linki eksik!");

            const username = sessionStorage.getItem("username");

            if (!username) {
                alert("Analiz yapabilmek için lütfen önce giriş yapın!");
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';

            try {
                const res = await fetch('http://127.0.0.1:8000/api/analiz-et', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url: url, username: username }) 
                });
                
                if (!res.ok) {
                    const errorData = await res.json();
                    throw new Error(errorData.detail || "API hatası. Status: " + res.status);
                }
                
                const data = await res.json();

                localStorage.setItem("lastAnalysisData", JSON.stringify(data));
                localStorage.setItem("lastUrl", url);

                if (typeof updateDashboardUI === "function") {
                    updateDashboardUI(data);
                } else {
                    console.error("[ANALIZ] updateDashboardUI fonksiyonu bulunamadı!");
                }

                if (typeof loadAnalysisHistory === "function") {
                    loadAnalysisHistory(); 
                }

                // YENİ: Analiz bittiği an Takip durumunu arka planda sorgula!
                if (typeof checkTrackingStatus === "function") {
                    checkTrackingStatus(username, url);
                }

            } catch (err) {
                alert("Sistem Hatası: " + err.message);
                document.getElementById('loading').style.display = 'none';
            }
        });
    }
});


// ==========================================
// 2. YARDIMCI FONKSİYONLAR (BİLDİRİM VE ARAÇLAR)
// ==========================================

function bildirimGoster(mesaj, basariliMi = true) {
    let toast = document.getElementById('cyberToast');
    
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'cyberToast';
        document.body.appendChild(toast);
    }

    const ikon = basariliMi 
        ? '<i class="fa-solid fa-circle-check text-success fs-3"></i>' 
        : '<i class="fa-solid fa-triangle-exclamation text-danger fs-3"></i>';
    const sinif = basariliMi ? 'toast-success' : 'toast-error';
    
    toast.className = `cyber-toast ${sinif}`;
    toast.innerHTML = `${ikon} <div style="margin-left: 10px;">${mesaj}</div>`;

    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => toast.classList.remove('show'), 3500);
}

// Şifre Göster/Gizle Fonksiyonu
function togglePassword(inputId, iconElement) {
    const input = document.getElementById(inputId);
    
    if (input.type === "password") {
        input.type = "text";
        iconElement.classList.remove("fa-eye");
        iconElement.classList.add("fa-eye-slash"); 
    } else {
        input.type = "password";
        iconElement.classList.remove("fa-eye-slash");
        iconElement.classList.add("fa-eye"); 
    }
}


// ==========================================
// 3. KİMLİK DOĞRULAMA (LOGIN, REGISTER, LOGOUT)
// ==========================================
function logout() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = "login.html";
}

// --- GÜVENLİ 2FA GİRİŞ MEKANİZMASI (login.html) ---
if (window.location.pathname.toLowerCase().includes("login.html")) {
    
    const btnLoginStep1 = document.getElementById("btnLoginStep1");
    const btnVerifyStep2 = document.getElementById("btnVerifyStep2");
    const credentialsStep = document.getElementById("credentialsStep");
    const codeStep = document.getElementById("codeStep");
    const otpMessage = document.getElementById("otpMessage");
    
    const errorBox = document.getElementById("loginError");
    const errorText = document.getElementById("errorText");
    
    let currentUsername = ""; 

    function showError(message) {
        errorText.innerText = message;
        errorBox.style.display = "block";
    }

    if(btnLoginStep1) {
        btnLoginStep1.addEventListener("click", async () => {
            errorBox.style.display = "none"; 
            
            const user = document.getElementById("loginUser").value.trim();
            const pass = document.getElementById("loginPass").value.trim();
            const cfToken = typeof turnstile !== 'undefined' ? turnstile.getResponse() : "";

            if (!user || !pass) return showError("Kullanıcı adı ve şifre zorunludur!");
            if (!cfToken) return showError("Lütfen bot doğrulamasını (Captcha) tamamlayın.");

            btnLoginStep1.disabled = true;
            btnLoginStep1.innerText = "Kimlik Doğrulanıyor...";

            try {
                const response = await fetch("http://127.0.0.1:8000/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: user, password: pass, cf_token: cfToken })
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.detail || "Giriş başarısız.");

                currentUsername = user; 
                
                document.getElementById("headerStep1").style.display = "none";
                document.getElementById("headerStep2").style.display = "block";
                credentialsStep.style.display = "none";
                codeStep.style.display = "block";
                otpMessage.innerText = data.message; 
                document.getElementById("authCode").focus();

            } catch (err) {
                showError(err.message); 
                btnLoginStep1.disabled = false;
                btnLoginStep1.innerText = "Giriş Yap";
                if(typeof turnstile !== 'undefined') turnstile.reset(); 
            }
        });
    }

    if(btnVerifyStep2) {
        btnVerifyStep2.addEventListener("click", async () => {
            errorBox.style.display = "none"; 
            
            const code = document.getElementById("authCode").value.trim();

            if (code.length !== 6 || isNaN(code)) return showError("Lütfen 6 haneli kodu eksiksiz girin.");

            btnVerifyStep2.disabled = true;
            btnVerifyStep2.innerText = "Doğrulanıyor...";

            try {
                const response = await fetch("http://127.0.0.1:8000/api/verify-login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: currentUsername, code: code })
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.detail || "Doğrulama başarısız.");

                sessionStorage.setItem("isLoggedIn", "true");
                sessionStorage.setItem("username", currentUsername);
                window.location.href = "index.html"; 

            } catch (err) {
                showError(err.message); 
                btnVerifyStep2.disabled = false;
                btnVerifyStep2.innerText = "Doğrula ve Sisteme Gir";
                
                if (err.message.includes("iptal edildi") || err.message.includes("baştan giriş")) {
                    setTimeout(() => window.location.reload(), 2500); 
                }
            }
        });
    }
}

// --- GÜVENLİ 2FA KAYIT MEKANİZMASI (register.html) ---
if (window.location.pathname.toLowerCase().includes("register.html")) {
    const btnRegisterStep1 = document.getElementById("btnRegisterStep1");
    const btnRegisterStep2 = document.getElementById("btnRegisterStep2");
    const regInfoStep = document.getElementById("regInfoStep");
    const regCodeStep = document.getElementById("regCodeStep");
    const regOtpMessage = document.getElementById("regOtpMessage");
    
    const msgBox = document.getElementById("regMessage");
    const msgText = document.getElementById("regMsgText");
    
    let pendingUsername = ""; 

    function showRegMessage(message, isError = true) {
        msgBox.style.background = isError ? "rgba(239, 68, 68, 0.1)" : "rgba(34, 197, 94, 0.1)";
        msgBox.style.color = isError ? "#ef4444" : "#4ade80";
        msgBox.style.border = isError ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(34, 197, 94, 0.3)";
        msgText.innerHTML = isError ? `<i class="fa-solid fa-triangle-exclamation"></i> ${message}` : `<i class="fa-solid fa-check-circle"></i> ${message}`;
        msgBox.style.display = "block";
    }

    if(btnRegisterStep1) {
        btnRegisterStep1.addEventListener("click", async () => {
            msgBox.style.display = "none";
            
            const user = document.getElementById("regUser").value.trim();
            const email = document.getElementById("regEmail").value.trim();
            const phone = document.getElementById("regPhone").value.trim();
            const pass = document.getElementById("regPass").value;
            const passConfirm = document.getElementById("regPassConfirm").value;
            const cfToken = typeof turnstile !== 'undefined' ? turnstile.getResponse() : "";

            if (!user || !email || !pass) return showRegMessage("Zorunlu alanları doldurun.");
            if (pass !== passConfirm) return showRegMessage("Şifreler eşleşmiyor!");
            if (!cfToken) return showRegMessage("Lütfen bot doğrulamasını tamamlayın.");

            btnRegisterStep1.disabled = true;
            btnRegisterStep1.innerText = "Doğrulama Kodu Gönderiliyor...";

            try {
                const response = await fetch("http://127.0.0.1:8000/api/register-step1", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: user, email: email, phone: phone, password: pass, cf_token: cfToken })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "İşlem başarısız.");

                pendingUsername = user; 
                
                document.getElementById("regHeaderStep1").style.display = "none";
                document.getElementById("regHeaderStep2").style.display = "block";
                regInfoStep.style.display = "none";
                regCodeStep.style.display = "block";
                regOtpMessage.innerText = data.message; 
                document.getElementById("regAuthCode").focus();

            } catch (err) {
                showRegMessage(err.message);
                btnRegisterStep1.disabled = false;
                btnRegisterStep1.innerText = "Hesap Oluştur";
                if(typeof turnstile !== 'undefined') turnstile.reset(); 
            }
        });
    }

    if(btnRegisterStep2) {
        btnRegisterStep2.addEventListener("click", async () => {
            msgBox.style.display = "none";
            const code = document.getElementById("regAuthCode").value.trim();

            if (code.length !== 6 || isNaN(code)) return showRegMessage("6 haneli kodu eksiksiz girin.");

            btnRegisterStep2.disabled = true;
            btnRegisterStep2.innerText = "Kayıt Tamamlanıyor...";

            try {
                const response = await fetch("http://127.0.0.1:8000/api/register-step2", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: pendingUsername, code: code })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "Kayıt başarısız.");

                showRegMessage(data.message, false);
                
                setTimeout(() => {
                    window.location.href = "login.html"; 
                }, 2500);

            } catch (err) {
                showRegMessage(err.message);
                btnRegisterStep2.disabled = false;
                btnRegisterStep2.innerText = "Kaydı Tamamla";
                
                if (err.message.includes("iptal edildi") || err.message.includes("baştan kayıt")) {
                    setTimeout(() => window.location.reload(), 2500); 
                }
            }
        });
    }
}


// ==========================================
// 4. ŞİFRE KURTARMA (FORGOT PASSWORD)
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    const forgotStep1 = document.getElementById("forgotStep1");
    const forgotStep2 = document.getElementById("forgotStep2");
    
    const btnSendResetCode = document.getElementById("btnSendResetCode");
    const btnUpdatePass = document.getElementById("btnUpdatePass");

    let tempEmail = ""; 

    if (btnSendResetCode) {
        btnSendResetCode.addEventListener("click", async () => {
            const email = document.getElementById("forgotEmail").value.trim();
            if (!email) return bildirimGoster("Lütfen e-posta adresinizi girin.", false);

            const orijinalMetin = btnSendResetCode.innerHTML;
            btnSendResetCode.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kod Gönderiliyor...';
            btnSendResetCode.disabled = true;

            try {
                const response = await fetch("http://127.0.0.1:8000/api/forgot-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail);

                tempEmail = email; 
                bildirimGoster(data.message, true);
                
                forgotStep1.style.display = "none";
                forgotStep2.style.display = "block";

            } catch (error) {
                bildirimGoster(error.message, false);
            } finally {
                btnSendResetCode.innerHTML = orijinalMetin;
                btnSendResetCode.disabled = false;
            }
        });
    }

    if (btnUpdatePass) {
        btnUpdatePass.addEventListener("click", async () => {
            const code = document.getElementById("forgotCode").value.trim();
            const newPass = document.getElementById("forgotNewPass").value;

            if (code.length !== 6 || !newPass) {
                return bildirimGoster("Lütfen kodu (6 hane) ve yeni şifrenizi eksiksiz girin.", false);
            }

            const orijinalMetin = btnUpdatePass.innerHTML;
            btnUpdatePass.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Güncelleniyor...';
            btnUpdatePass.disabled = true;

            try {
                const response = await fetch("http://127.0.0.1:8000/api/reset-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: tempEmail, code: code, new_password: newPass })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail);

                bildirimGoster("Şifreniz başarıyla yenilendi! Giriş sayfasına yönlendiriliyorsunuz...", true);
                
                setTimeout(() => {
                    window.location.href = "login.html"; 
                }, 2000);

            } catch (error) {
                bildirimGoster(error.message, false);
            } finally {
                btnUpdatePass.innerHTML = orijinalMetin;
                btnUpdatePass.disabled = false;
            }
        });
    }
});


// ==========================================
// 5. PROFİL, AMAZON AYARLARI VE HESAP SİLME
// ==========================================
async function saveAmazonCredentials() {
    const username = sessionStorage.getItem("username") || localStorage.getItem("username");
    const email = document.getElementById('amazonEmail').value;
    const pass = document.getElementById('amazonPass').value;
    const msg = document.getElementById('saveMsg');

    try {
        const res = await fetch('http://127.0.0.1:8000/api/update-amazon', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                username: username, 
                amazon_email: email, 
                amazon_password: pass 
            })
        });

        if (res.ok) {
            msg.style.display = 'block';
            setTimeout(() => msg.style.display = 'none', 3000);
        } else {
            alert("Amazon bilgileri kaydedilemedi.");
        }
    } catch (err) {
        alert("Bağlantı hatası! Sunucu açık mı?");
    }
}

async function loadUserProfile() {
    const username = sessionStorage.getItem("username") || localStorage.getItem("username");
    if(!username || !document.getElementById('profUser')) return;

    try {
        const res = await fetch(`http://127.0.0.1:8000/api/user-info/${username}`);
        const data = await res.json();
        if(res.ok) {
            document.getElementById('profUser').value = data.username;
            document.getElementById('profEmail').value = data.email;
            document.getElementById('profPhone').value = data.phone;
            
            if(document.getElementById('amazonEmail')) {
                document.getElementById('amazonEmail').value = data.amazon_email || "";
                document.getElementById('amazonPass').value = data.amazon_password || "";
            }
        }
    } catch (err) { console.error("[loadUserProfile] Profil yüklenemedi: " + err.message); }
}

async function updateUserProfile() {
    const username = sessionStorage.getItem("username") || localStorage.getItem("username");
    const email = document.getElementById('profEmail').value;
    const phone = document.getElementById('profPhone').value;
    const pass = document.getElementById('profPass').value;
    const passConfirm = document.getElementById('profPassConfirm').value;
    const msg = document.getElementById('profMsg');

    if (pass !== "" || passConfirm !== "") {
        if (pass !== passConfirm) {
            msg.style.display = 'block';
            msg.className = "mt-3 text-center text-danger fw-bold";
            msg.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Yeni şifreler eşleşmiyor!`;
            
            document.getElementById('profPass').style.borderColor = "#ef4444";
            document.getElementById('profPassConfirm').style.borderColor = "#ef4444";
            return; 
        }
    }

    try {
        const res = await fetch('http://127.0.0.1:8000/api/update-profile', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                current_user: username, 
                email: email, 
                phone: phone, 
                password: pass || null 
            })
        });

        const data = await res.json();
        msg.style.display = 'block';
        msg.className = "mt-3 text-center " + (res.ok ? "text-success fw-bold" : "text-danger fw-bold");
        msg.innerHTML = res.ok ? `<i class="fa-solid fa-check-circle"></i> ${data.message}` : data.detail;
        
        if(res.ok) {
            document.getElementById('profPass').value = "";
            document.getElementById('profPassConfirm').value = "";
            document.getElementById('profPass').style.borderColor = "var(--border-subtle)";
            document.getElementById('profPassConfirm').style.borderColor = "var(--border-subtle)";
        }
    } catch (err) { 
        alert("Bağlantı hatası! Sunucu açık mı?"); 
    }
}

// 1. Profil sayfasındaki kırmızı "Hesabımı Sil" butonuna tıklandığında sadece Modalı açar
function hesabiKalicilOlarakSil() {
    const deleteModal = new bootstrap.Modal(document.getElementById('accountDeleteModal'));
    deleteModal.show();
}

// 2. Modalın içindeki Kırmızı Onay Butonuna ("Evet, Sil") Tıklandığında
document.addEventListener("DOMContentLoaded", () => {
    const btnConfirmAccountDelete = document.getElementById("btnConfirmAccountDelete");
    
    if (btnConfirmAccountDelete) {
        btnConfirmAccountDelete.addEventListener("click", async () => {
            const username = sessionStorage.getItem("username");
            if (!username) return;

            const originalText = btnConfirmAccountDelete.innerHTML;
            btnConfirmAccountDelete.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Siliniyor...';
            btnConfirmAccountDelete.disabled = true;

            try {
                const res = await fetch(`http://127.0.0.1:8000/api/users/${encodeURIComponent(username)}`, {
                    method: "DELETE"
                });
                
                if (res.ok) {
                    bildirimGoster("Hesabınız silindi.", true);
                    
                    setTimeout(() => {
                        sessionStorage.clear();
                        localStorage.clear();
                        window.location.href = "login.html";
                    }, 2000);
                } else {
                    bildirimGoster("Ağ hatası! İşlem başarısız oldu.", false);
                }
            } catch (e) {
                console.error("Hesap silme hatası:", e);
                bildirimGoster("Sistem hatası: Sunucu ile iletişim kurulamadı.", false);
            } finally {
                const modalEl = document.getElementById('accountDeleteModal');
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) {
                    modalInstance.hide();
                }
                
                btnConfirmAccountDelete.innerHTML = originalText;
                btnConfirmAccountDelete.disabled = false;
            }
        });
    }
});


// ==========================================
// 6. ANALİZ SONUÇLARI, GRAFİKLER VE FİLTRELEME (DASHBOARD)
// ==========================================
let myChart = null;
let globalReviews = [];

function updateDashboardUI(data) {
    try {
        console.log("[updateDashboardUI] Başladı");
        document.getElementById('loading').style.display = 'none';
        document.getElementById('results').style.display = 'block';

        document.getElementById('toplamYorum').innerText = data.ozet.toplam_yorum;
        document.getElementById('gercekYorum').innerText = data.ozet.gercek_yorum_sayisi;
        document.getElementById('sahteYorum').innerText = data.ozet.sahte_yorum_sayisi;
        document.getElementById('sahtelikOrani').innerText = "%" + data.ozet.sahtelik_orani;
        document.getElementById('riskBar').style.width = data.ozet.sahtelik_orani + "%";

        let gercekYuzdesi = Math.round((data.ozet.gercek_yorum_sayisi / data.ozet.toplam_yorum) * 100);
        if (isNaN(gercekYuzdesi)) gercekYuzdesi = 0;
        document.getElementById('chart-percentage').innerText = "%" + gercekYuzdesi;
        document.getElementById('chart-center-text').style.display = 'block';

        const ctx = document.getElementById('sonucGrafigi').getContext('2d');
        if(myChart) myChart.destroy();
        
        Chart.defaults.color = '#a1a1aa';
        Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
        
        myChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Gerçek', 'Sahte'],
                datasets: [{
                    data: [data.ozet.gercek_yorum_sayisi, data.ozet.sahte_yorum_sayisi],
                    backgroundColor: ['#16a34a', '#dc2626'],
                    borderColor: ['#14532d', '#7f1d1d'],
                    borderWidth: 2,
                    hoverOffset: 5
                }]
            },
            options: { cutout: '75%', plugins: { legend: { position: 'bottom' } } }
        });
        
        const gercekData = [0, 0, 0, 0, 0]; 
        const sahteData = [0, 0, 0, 0, 0]; 

        if (data && data.yorumlar) {
            data.yorumlar.forEach(item => {
                let score = parseFloat(item.guven_skoru); 
                if (score <= 1) score = score * 100;

                let index = Math.floor(score / 20);
                if (index > 4) index = 4;
                if (index < 0) index = 0;

                if (item.karar === 'GERÇEK') gercekData[index]++;
                else if (item.karar === 'SAHTE') sahteData[index]++;
            });
        }

        const ctx2 = document.getElementById('ikinciGrafik').getContext('2d');
        if (window.myBarChart) window.myBarChart.destroy();

        window.myBarChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: ['%0-20', '%20-40', '%40-60', '%60-80', '%80-100'],
                datasets: [
                    {
                        label: 'Gerçek',
                        data: gercekData,
                        backgroundColor: '#16a34a', 
                        borderColor: '#14532d',
                        borderWidth: 1,
                        borderRadius: 4,
                        barPercentage: 0.8,
                        categoryPercentage: 0.8
                    },
                    {
                        label: 'Sahte',
                        data: sahteData,
                        backgroundColor: '#dc2626', 
                        borderColor: '#7f1d1d',
                        borderWidth: 1,
                        borderRadius: 4,
                        barPercentage: 0.8,
                        categoryPercentage: 0.8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { color: '#a1a1aa', font: { size: 12 }, usePointStyle: true, padding: 20 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255, 255, 255, 0.1)', borderWidth: 1
                    }
                },
                scales: {
                    y: { beginAtZero: true, suggestedMax: 5, grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }, ticks: { color: '#a1a1aa', stepSize: 1 } },
                    x: { grid: { display: false }, ticks: { color: '#a1a1aa' } }
                }
            }
        });

        const stopWords = ['ve', 'bir', 'bu', 'da', 'de', 'için', 'ile', 'çok', 'gibi', 'the', 'a', 'to', 'and', 'is', 'it', 'in', 'of', 'for', 'i', 'this', 'that', 'my', 'on', 'with', 'was', 'very', 'good', 'nice', 'great'];
        const kelimeHavuzu = {};

        if (data && data.yorumlar) {
            data.yorumlar.forEach(item => {
                if (item.karar === 'SAHTE' && item.metin) {
                    let kelimeler = item.metin.toLowerCase().match(/[a-zğüşöçı]+/g);
                    if (kelimeler) {
                        kelimeler.forEach(kelime => {
                            if (kelime.length > 3 && !stopWords.includes(kelime)) {
                                kelimeHavuzu[kelime] = (kelimeHavuzu[kelime] || 0) + 1;
                            }
                        });
                    }
                }
            });
        }

        const enCokGecenler = Object.entries(kelimeHavuzu).sort((a, b) => b[1] - a[1]).slice(0, 6);
        const kelimeEtiketleri = enCokGecenler.map(k => k[0].toUpperCase());
        const kelimeSayilari = enCokGecenler.map(k => k[1]);

        const ctxKelime = document.getElementById('kelimeGrafigi').getContext('2d');
        if (window.myKelimeChart) window.myKelimeChart.destroy();
        
        window.myKelimeChart = new Chart(ctxKelime, {
            type: 'bar',
            data: {
                labels: kelimeEtiketleri,
                datasets: [{
                    label: 'Tekrar Sayısı',
                    data: kelimeSayilari,
                    backgroundColor: '#6366f1',
                    borderColor: '#3730a3',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { stepSize: 1, color: '#a1a1aa' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#e2e8f0', font: { weight: '600' } }, grid: { display: false } }
                }
            }
        });

        const scatterData = [];

        if (data && data.yorumlar) {
            data.yorumlar.forEach(item => {
                if (item.karar === 'SAHTE' && item.metin) {
                    let kelimeSayisi = item.metin.trim().split(/\s+/).length;
                    let skor = parseFloat(item.guven_skoru);
                    if (skor <= 1) skor = skor * 100;
                    scatterData.push({ x: kelimeSayisi, y: skor });
                }
            });
        }

        const ctxUzunluk = document.getElementById('uzunlukGrafigi').getContext('2d');
        if (window.myUzunlukChart) window.myUzunlukChart.destroy();

        window.myUzunlukChart = new Chart(ctxUzunluk, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Sahte Yorum (Bot)',
                    data: scatterData,
                    backgroundColor: '#dc2626',
                    borderColor: '#7f1d1d',
                    borderWidth: 1,
                    pointRadius: 6,
                    pointHoverRadius: 9
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        borderColor: '#7f1d1d',
                        borderWidth: 1,
                        callbacks: {
                            label: function(ctx) {
                                return `Uzunluk: ${ctx.parsed.x} Kelime | Skor: %${ctx.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: { title: { display: true, text: 'Sahtelik Skoru (%)', color: '#a1a1aa' }, ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { title: { display: true, text: 'Kelime Sayısı', color: '#a1a1aa' }, ticks: { color: '#a1a1aa' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });

        globalReviews = data.yorumlar;
        document.getElementById('filter-panel').style.display = 'flex';
        applyFilters();
        console.log("[updateDashboardUI] Tamamlandı");
    } catch (err) {
        console.error("[updateDashboardUI] Hata oluştu: " + err.message);
        alert("Dashboard güncellenirken hata: " + err.message);
        document.getElementById('loading').style.display = 'none';
    }
}

function restoreDashboard() {
    try {
        const savedData = localStorage.getItem("lastAnalysisData");
        const savedUrl = localStorage.getItem("lastUrl");
        
        console.log("[restoreDashboard] Kontrol: savedData=" + (savedData ? "var" : "yok") + ", savedUrl=" + (savedUrl ? "var" : "yok"));
        
        if (savedData && savedUrl && document.getElementById('results')) {
            console.log("[restoreDashboard] Veri restore ediliyor...");
            document.getElementById('amazonUrl').value = savedUrl; 
            const data = JSON.parse(savedData); 
            updateDashboardUI(data);
            
            // 🚀 Sayfa yenilendiğinde de takip durumunu kontrol et
            const username = sessionStorage.getItem("username");
            checkTrackingStatus(username, savedUrl);
            
            console.log("[restoreDashboard] Restore tamamlandı");
        } else {
            console.log("[restoreDashboard] Restore şartları sağlanmadı");
        }
    } catch (err) {
        console.error("[restoreDashboard] Hata: " + err.message);
    }
}

function applyFilters() {
    if(!document.getElementById("filter-status")) return; 
    
    const statusFilter = document.getElementById("filter-status").value;
    const confidenceFilter = document.getElementById("filter-confidence").value;
    const sortOrder = document.getElementById("sort-order").value;

    let filteredReviews = [...globalReviews];

    filteredReviews = filteredReviews.filter(review => {
        if (statusFilter !== "ALL" && review.karar !== statusFilter) return false;
        if (confidenceFilter === "HIGH" && review.guven_skoru < 90) return false;
        if (confidenceFilter === "LOW" && review.guven_skoru >= 70) return false;
        return true;
    });

    if (sortOrder === "DESC") filteredReviews.sort((a, b) => b.guven_skoru - a.guven_skoru);
    else if (sortOrder === "ASC") filteredReviews.sort((a, b) => a.guven_skoru - b.guven_skoru);

    renderReviews(filteredReviews);
}

function renderReviews(reviewsToRender) {
    const list = document.getElementById('yorumListesi');
    if (reviewsToRender.length === 0) {
        list.innerHTML = `<tr><td colspan="3" class="text-center text-warning py-4"><i class="fa-solid fa-triangle-exclamation mb-2 fs-3"></i><br>Sonuç bulunamadı.</td></tr>`;
        return;
    }
    list.innerHTML = reviewsToRender.map(y => {
        const isFake = y.karar !== 'GERÇEK';
        const icon = isFake ? '<i class="fa-solid fa-robot"></i>' : '<i class="fa-solid fa-user-check"></i>';
        return `
        <tr>
            <td><span class="badge ${isFake ? 'badge-sahte' : 'badge-gercek'} rounded-pill px-3 py-2">${icon} &nbsp;${y.karar}</span></td>
            <td><span class="fw-bold ${isFake ? 'text-danger' : 'text-success'}" style="font-size: 1.1rem;">%${y.guven_skoru}</span></td>
            <td><div style="font-size: 0.9rem; line-height: 1.5; color: #e2e8f0;">${y.metin.substring(0, 150)}...</div></td>
        </tr>
        `;
    }).join('');
}


// ==========================================
// 7. GEÇMİŞ (HISTORY), ÜRÜN TAKİBİ VE FAVORİLER
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    loadAnalysisHistory();
    loadFavorites(); 
});

function loadAnalysisHistory() {
    const tableBody = document.getElementById("historyTableBody");
    if (!tableBody) return;

    const currentUsername = sessionStorage.getItem("username");

    if (!currentUsername) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-warning py-4">Lütfen geçmişinizi görmek için sisteme giriş yapın.</td></tr>`;
        return;
    }

    fetch(`http://127.0.0.1:8000/api/analyses/history?username=${currentUsername}`)
        .then(response => {
            if (!response.ok) throw new Error("Backend'den yanıt alınamadı.");
            return response.json();
        })
        .then(res => {
            if (res.status === "success" && res.data.length > 0) {
                tableBody.innerHTML = ""; 
                
                res.data.forEach(item => {
                    const badgeClass = item.risk_score > 50 ? "badge-sahte" : "badge-gercek";
                    const badgeText = item.risk_score > 50 ? `%${item.risk_score} Yüksek Risk` : `%${item.risk_score} Riskli`;
                    const shortUrl = item.target_url.length > 50 ? item.target_url.substring(0, 50) + "..." : item.target_url;

                    const row = `
                        <tr>
                            <td style="font-family: monospace; font-size: 0.85rem; color: #a1a1aa;">${item.created_at}</td>
                            <td><a href="${item.target_url}" target="_blank" class="text-white text-decoration-none small" style="text-decoration: underline !important;">${shortUrl}</a></td>
                            <td style="color: #e2e8f0;"><i class="fa-regular fa-comment-dots me-1" style="color: var(--primary-color);"></i> ${item.analyzed_comments_count} adet</td>
                            <td><span class="${badgeClass}">${badgeText}</span></td>
                            <td class="text-center">
                                <a href="http://127.0.0.1:8000/api/export-pdf/${item.id}" target="_blank" download class="btn btn-sm" style="border: 1px solid var(--border-subtle); color: #ffffff;">
                                    <i class="fa-solid fa-file-pdf me-1"></i> PDF İndir
                                </a>
                            </td>
                        </tr>
                    `;
                    tableBody.innerHTML += row;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-white py-4">Henüz yapılmış bir analiz bulunmuyor.</td></tr>`;
            }
        })
        .catch(err => {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Veriler çekilirken bir hata oluştu: ${err.message}</td></tr>`;
        });
}

// DURUMU KONTROL FONKSİYONU
async function checkTrackingStatus(username, url) {
    const btn = document.getElementById("btnTakibeAl");
    if (!btn || !username || !url) return;

    btn.style.border = "1px solid #f59e0b";
    btn.style.color = "#f59e0b";
    btn.style.background = "transparent";
    btn.innerHTML = '<i class="fa-solid fa-bell me-2"></i> BU ÜRÜNÜ TAKİBE AL ';
    btn.disabled = false;

    try {
        const res = await fetch(`http://127.0.0.1:8000/api/check-tracking?username=${encodeURIComponent(username)}&url=${encodeURIComponent(url)}`);
        const data = await res.json();
        
        if (data.is_tracked) {
            btn.style.border = "1px solid #16a34a";
            btn.style.color = "#16a34a";
            btn.style.background = "rgba(22, 163, 74, 0.1)";
            btn.innerHTML = '<i class="fa-solid fa-check me-2"></i> TAKİBE ALINDI';
            btn.disabled = true; 
        }
    } catch(e) {
        console.log("Takip kontrolü yapılamadı:", e);
    }
}

// TAKİBE AL BUTONU OLAYI
document.addEventListener("DOMContentLoaded", function() {
    const btnTakibeAl = document.getElementById("btnTakibeAl");
    
    if (btnTakibeAl) {
        btnTakibeAl.addEventListener("click", async function() {
            
            const username = sessionStorage.getItem("username");
            const targetUrl = localStorage.getItem("lastUrl") || document.getElementById('amazonUrl').value;
            const lastDataStr = localStorage.getItem("lastAnalysisData");

            if (!username) return alert("Ürünleri takip edebilmek için sisteme giriş yapmalısınız!");
            if (!targetUrl || !lastDataStr) return alert("Önce tarama yapmalısınız.");

            const lastData = JSON.parse(lastDataStr);
            const initialScore = lastData.ozet ? (lastData.ozet.sahtelik_orani || 0) : (lastData.risk_score || 0);
            const originalText = btnTakibeAl.innerHTML;

            btnTakibeAl.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> RADARA EKLENİYOR...';
            btnTakibeAl.disabled = true;

            try {
                const res = await fetch("http://127.0.0.1:8000/api/track", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        username: username,
                        url: targetUrl,
                        initial_score: initialScore
                    })
                });

                const responseData = await res.json();

                if (res.ok) {
                    btnTakibeAl.style.border = "1px solid #16a34a";
                    btnTakibeAl.style.color = "#16a34a";
                    btnTakibeAl.style.background = "rgba(22, 163, 74, 0.1)";
                    btnTakibeAl.innerHTML = '<i class="fa-solid fa-check me-2"></i> TAKİBE ALINDI';
                    btnTakibeAl.disabled = true; 
                } else {
                    throw new Error(responseData.detail || "Sisteme eklenemedi.");
                }

            } catch (err) {
                alert("Uyarı: " + err.message);
                btnTakibeAl.innerHTML = originalText;
                btnTakibeAl.disabled = false;
            }
        });
    }
});

// FAVORİLER (TAKİP EDİLENLER) SAYFASINI DOLDURMA
function loadFavorites() {
    const tableBody = document.getElementById("favoriteTableBody");
    if (!tableBody) return; 

    const currentUsername = sessionStorage.getItem("username");

    if (!currentUsername) {
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-warning py-4">Favorilerinizi görmek için sisteme giriş yapmalısınız.</td></tr>`;
        return;
    }

    fetch(`http://127.0.0.1:8000/api/favorites?username=${encodeURIComponent(currentUsername)}`)
        .then(res => res.json())
        .then(res => {
            if (res.status === "success" && res.data.length > 0) {
                tableBody.innerHTML = ""; 

                res.data.forEach(item => {
                    const badgeClass = item.last_risk_score > 50 ? "badge-sahte" : "badge-gercek";
                    const badgeText = item.last_risk_score > 50 ? `%${item.last_risk_score} Riskli` : `%${item.last_risk_score} Riskli`;
                    const shortUrl = item.target_url.length > 50 ? item.target_url.substring(0, 50) + "..." : item.target_url;
                    const dateOnly = item.created_at.split(' ')[0];

                    const row = `
                        <tr>
                            <td style="font-family: monospace; font-size: 0.85rem; color: #a1a1aa;">${dateOnly}</td>
                            <td><a href="${item.target_url}" target="_blank" class="text-white text-decoration-none small" style="text-decoration: underline !important;">${shortUrl}</a></td>
                            <td style="color: #16a34a;"><i class="fa-solid fa-satellite-dish me-1"></i> Radar Aktif</td>
                            <td><span class="${badgeClass}">${badgeText}</span></td>
                            <td class="text-center">
                                <button class="btn btn-sm btn-outline-danger" onclick="removeFromFavorites(${item.id})">
                                    <i class="fa-solid fa-trash-can"></i> Sil
                                </button>
                            </td>
                        </tr>
                    `;
                    tableBody.innerHTML += row;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-white py-4">Henüz radara aldığınız bir ürün bulunmuyor.</td></tr>`;
            }
        })
        .catch(err => {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Veriler çekilirken bir hata oluştu.</td></tr>`;
        });
}

// --- FAVORİLERDEN SİLME İŞLEMİ (MODAL İLE) ---

let currentDeleteItemId = null; 

// 1. Tablodaki "Sil" butonuna tıklandığında sadece Modalı açar
function removeFromFavorites(itemId) {
    currentDeleteItemId = itemId; 
    
    // Bootstrap JS artık sayfada olduğu için bu kod hatasız çalışacak
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    deleteModal.show();
}

// 2. Modalın içindeki Kırmızı Onay Butonuna Tıklandığında
document.addEventListener("DOMContentLoaded", () => {
    const btnConfirmDelete = document.getElementById("btnConfirmDelete");
    
    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener("click", async () => {
            if (!currentDeleteItemId) return;

            const originalText = btnConfirmDelete.innerHTML;
            btnConfirmDelete.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Siliniyor...';
            btnConfirmDelete.disabled = true;

            try {
                const res = await fetch(`http://127.0.0.1:8000/api/favorites/${currentDeleteItemId}`, {
                    method: "DELETE"
                });
                
                if (res.ok) {
                    bildirimGoster("Ürün radar takibinden çıkarıldı. Bekçi geri çekildi.", true);
                    loadFavorites(); 
                } else {
                    bildirimGoster("Ağ hatası! Silme işlemi başarısız oldu.", false);
                }
            } catch (e) {
                console.error("Silme hatası:", e);
                bildirimGoster("Sistem hatası: Sunucu ile iletişim kurulamadı.", false);
            } finally {
                const deleteModalEl = document.getElementById('deleteConfirmModal');
                const deleteModalInstance = bootstrap.Modal.getInstance(deleteModalEl);
                if (deleteModalInstance) {
                    deleteModalInstance.hide();
                }
                
                btnConfirmDelete.innerHTML = originalText;
                btnConfirmDelete.disabled = false;
                currentDeleteItemId = null;
            }
        });
    }
});


// ==========================================
// 8. İLETİŞİM FORMU (CONTACT)
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    const contactForm = document.getElementById("contactForm");

    if (contactForm) {
        contactForm.addEventListener("submit", async (e) => {
            e.preventDefault(); 

            const name = document.getElementById("name").value.trim();
            const email = document.getElementById("email").value.trim();
            const message = document.getElementById("message").value.trim();
            
            if (!name || !email || !message) {
                bildirimGoster("Lütfen tüm zorunlu alanları doldurun.", false);
                return;
            }

            const submitBtn = contactForm.querySelector("button[type='submit']");
            const originalText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gönderiliyor...';
            submitBtn.disabled = true;

            try {
                const response = await fetch("http://127.0.0.1:8000/api/communication", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: name, email: email, message: message })
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.detail || "Mail gönderilemedi.");

                bildirimGoster(data.message, true);
                contactForm.reset();

            } catch (error) {
                bildirimGoster(error.message, false);
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }
});