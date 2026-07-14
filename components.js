class CyberNavbar extends HTMLElement {
    
    connectedCallback() {
        let currentPath = window.location.pathname.split("/").pop();
        if (currentPath === "") currentPath = "index.html";

        this.innerHTML = `
            <nav class="cyber-navbar">
                <div class="logo">
                    <a href="index.html" style="text-decoration: none; display: flex; align-items: center; gap: 10px;">
                        <img src="images/logo2.png" style="height: 45px; width: auto;">
                    </a>
                </div>
                
                <div class="d-flex align-items-center">
                    <a href="index.html" class="nav-link-custom ${currentPath === 'index.html' ? 'active' : ''}">
                        <i class="fa-solid fa-chart-line"></i>
                        <span class="nav-text">Analiz</span>
                    </a>
                    <a href="compare.html" class="nav-link-custom ${currentPath === 'compare.html' ? 'active' : ''}">
                        <i class="fa-solid fa-arrows-h"></i>
                        <span class="nav-text">Karşılaştırma</span>
                    </a>
                    <a href="favorites.html" class="nav-link-custom ${currentPath === 'favorites.html' ? 'active' : ''}">
                        <i class="fa-solid fa-bell"></i>
                        <span class="nav-text">Favorilerim</span>
                    </a>
                    <a href="profile.html" class="nav-link-custom ${currentPath === 'profile.html' ? 'active' : ''}">
                        <i class="fa-solid fa-user"></i>
                        <span class="nav-text">Profil</span>
                    </a>
                    <a href="admin.html" id="adminMenuItem" class="nav-link-custom ${currentPath === 'admin.html' ? 'active' : ''}" style="display: none; ">
                        <i class="fa-solid fa-user-secret"></i>
                        <span class="nav-text">Admin Paneli</span>
                    </a>
                    <a href="history.html" class="nav-link-custom ${currentPath === 'history.html' ? 'active' : ''}">
                        <i class="fa-solid fa-history"></i>
                        <span class="nav-text">Geçmiş</span>
                    </a>
                    <a href="directory.html" class="nav-link-custom ${currentPath === 'directory.html' ? 'active' : ''}">
                        <i class="fa-solid fa-file-text"></i>
                        <span class="nav-text">Nasıl Anlaşılır?</span>
                    </a>
                    <a href="faq.html" class="nav-link-custom ${currentPath === 'faq.html' ? 'active' : ''}">
                        <i class="fa-solid fa-circle-question"></i>
                        <span class="nav-text">S.S.S</span>
                    </a>                    
                    <a href="communication.html" class="nav-link-custom ${currentPath === 'communication.html' ? 'active' : ''}">
                        <i class="fa-solid fa-phone"></i>
                        <span class="nav-text">İletişim</span>
                    </a>                    
                    <a href="#" class="nav-link-custom text-danger" onclick="logout()">
                        <i class="fa-solid fa-power-off"></i>
                        <span class="nav-text">Çıkış Yap</span>
                    </a>
                </div>
            </nav>
        `;

        const username = sessionStorage.getItem("username");
        if (username) {
            fetch(`http://127.0.0.1:8000/api/admin/check?username=${encodeURIComponent(username)}`)
            .then(res => res.json())
            .then(data => {
                if (data.is_admin) {
                    document.getElementById("adminMenuItem").style.display = "";
                }
            })
            .catch(err => console.error("Admin kontrolü başarısız:", err));
        }
    }
}

customElements.define('cyber-navbar', CyberNavbar);


class CyberFooter extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <footer class="mt-5 pt-5 pb-3" style="background: transparent; border-top: 1px solid var(--border-subtle);">
                <div class="container">
                    <div class="row gy-4">
                        
                        <div class="col-lg-4 col-md-6">
                            <div class="fs-4 fw-bold mb-3 text-white" style="font-family: 'Space Grotesk', sans-serif;">
                                <i class="fa-solid fa-radar me-2" style="color: var(--primary-color);"></i>Radar AI
                            </div>
                            <div class="text-white mb-3" style="font-size: 0.95rem; line-height: 1.6;">
                                Amazon yorumlarını yapay zeka ve derin öğrenme algoritmalarıyla saniyeler içinde analiz eden yeni nesil doğrulama motoru.
                            </div>
                        </div>

                        <div class="col-lg-4 col-md-6">
                            <div class="fs-5 fw-bold mb-3 text-white" style="font-family: 'Space Grotesk', sans-serif;">Hızlı Menü</div>
                            <ul class="list-unstyled">
                                <li class="mb-2">
                                    <a href="index.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> Analiz
                                    </a>
                                </li>
                                <li class="mb-2">
                                    <a href="compare.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> Karşılaştırma
                                    </a>
                                </li>
                                <li class="mb-2">
                                    <a href="directory.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> Nasıl Anlaşılır?
                                    </a>
                                </li>
                                <li class="mb-2">
                                    <a href="faq.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> Sıkça Sorulan Sorular
                                    </a>
                                </li>
                                <li class="mb-2">
                                    <a href="kvkk.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> KVKK
                                    </a>
                                </li>
                                <li class="mb-2">
                                    <a href="communication.html" class="text-white text-decoration-none footer-link">
                                        <i class="fa-solid fa-angle-right me-2" style="color: var(--primary-color); font-size: 0.8rem;"></i> İletişim
                                    </a>
                                </li>
                            </ul>
                        </div>

                        <div class="col-lg-4 col-md-12">
                            <div class="fs-5 fw-bold mb-3 text-white" style="font-family: 'Space Grotesk', sans-serif;">Bize Ulaşın</div>
                            <div class="text-white mb-2">
                                <i class="fa-solid fa-envelope me-2" style="color: var(--primary-color);"></i> contact.radarai@gmail.com
                            </div>
                            <div class="text-white mb-3">
                                <i class="fa-solid fa-location-dot me-2" style="color: var(--primary-color);"></i> İzmir, Türkiye
                            </div>
                            <div class="d-flex gap-3 mt-4">
                                <a href="https://www.instagram.com/?hl=tr" target="_blank" class="social-icon"><i class="fa-brands fa-instagram fs-4"></i></a>
                                <a href="https://wa.me/905050266158" target="_blank" class="social-icon"><i class="fa-brands fa-whatsapp fs-4"></i></a>
                                <a href="https://www.linkedin.com/?hl=tr" target="_blank" class="social-icon"><i class="fa-brands fa-linkedin fs-4"></i></a>
                                <a href="https://x.com/?lang=tr" target="_blank" class="social-icon"><i class="fa-brands fa-twitter fs-4"></i></a>
                            </div>
                        </div>
                    </div>

                    <hr class="mt-4 mb-3" style="border-color: var(--border-subtle);">
                    <div class="text-center text-white" style="font-size: 0.85rem;">
                        &copy; 2026 Radar AI. Tüm hakları saklıdır.
                    </div>
                </div>
                
                <style>
                    .footer-link { transition: all 0.3s ease; display: inline-block; }
                    .footer-link:hover { color: var(--primary-color) !important; transform: translateX(5px); }
                    .social-icon { color: #ffffff; transition: all 0.3s ease; }
                    .social-icon:hover { color: var(--primary-color); transform: translateY(-3px); }
                </style>
            </footer>
        `;
    }
}

customElements.define('cyber-footer', CyberFooter);