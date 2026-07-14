import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SENDER_EMAIL = "contact.radarai@gmail.com" 
SENDER_PASSWORD = "jmdw jutz ovxy keae"

def send_alert_email(receiver_email, product_url, old_score, new_score):
    subject = "DİKKAT: Takip Ettiğiniz Üründe Risk Artışı!"
    
    body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                        <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                            <h2 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">
                                Radar AI - Güvenlik Uyarısı
                            </h2>
                            <p>Merhaba,</p>
                            <p>Takip listenizdeki bir üründe ani bir bot/sahte yorum aktivitesi (risk artışı) tespit ettik.</p>
                            
                            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
                                <ul style="font-size: 16px; margin: 0; padding-left: 20px;">
                                    <li><b>Önceki Risk Skoru:</b> %{old_score}</li>
                                    <li><b>Yeni Risk Skoru:</b> <span style="color: #dc3545; font-weight: bold; font-size: 18px;">%{new_score}</span></li>
                                </ul>
                            </div>
                            
                            <p>Rakip firma veya satıcı manipülasyonu olabilir. Hemen incelemek için aşağıdaki bağlantıya tıklayın:</p>
                            <a href="{product_url}" style="display: inline-block; background-color: #00f3ff; color: #000; padding: 12px 20px; text-decoration: none; font-weight: bold; border-radius: 5px; margin-top: 10px;">
                                Ürünü İncele
                            </a>
                            
                            <br><br><hr style="border: 0; border-top: 1px solid #eee;">
                            <p style="font-size: 12px; color: #888; text-align: center;">
                                Bu mesaj SYS.LOG Radar AI sistemi tarafından otomatik olarak fırlatılmıştır. Lütfen yanıtlamayınız.
                            </p>
                        </div>
                    </body>
                </html>
            """
    msg = MIMEMultipart()
    msg['From'] = f"Radar AI <{SENDER_EMAIL}>"
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() 
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"E-posta {receiver_email}'a gönderildi.")
        return True
    except Exception as e:
        print(f"E-posta gönderilemedi: {e}")
        return False