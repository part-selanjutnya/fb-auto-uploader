import json
import os
import requests

# 1. Baca Konfigurasi
try:
    with open('config_twitter.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("File config_twitter.json tidak ditemukan!")
    exit()

if config.get("status_bot") == "OFF":
    print("Status bot sedang OFF. Pengintaian dihentikan.")
    exit()

# 2. Siapkan Token GitHub untuk Notifikasi (Issue)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

def kirim_notifikasi(judul, isi):
    if not GITHUB_TOKEN or not REPO_NAME:
        print(f" simulasi Notifikasi (Lokal): {judul}")
        return

    url = f"https://api.github.com/repos/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"title": judul, "body": isi}
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 201:
        print(f"✅ Notifikasi Issue berhasil dikirim ke GitHub: {judul}")
    else:
        print(f"❌ Gagal mengirim notifikasi: {res.text}")

def mulai_intai_alternatif():
    kata_kunci = [k.lower() for k in config.get("kata_kunci", [])]
    target_akun = config.get("target_akun", [])
    
    print("🚀 Memulai radar pengintaian dengan arsitektur stabil...")

    for akun in target_akun:
        print(f"🔍 Menyelidiki kanal publik untuk @{akun}...")
        try:
            # Menggunakan endpoint alternatif publik RSS/JSON feeder yang bersih dari gangguan HTML scraping
            url_feed = f"https://nitter.privacydev.net/{akun}/rss"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            response = requests.get(url_feed, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ Gagal mengakses kanal publik @{akun} (Status: {response.status_code})")
                continue
            
            # Ekstraksi data menggunakan parsing teks sederhana yang tahan banting
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Navigasi struktur RSS feed item
            items = root.findall('.//item')
            if not items:
                print(f"⚠️ Tidak ada entri data ditemukan pada @{akun}")
                continue

            for item in items[:5]: # Ambil 5 data terbaru
                title_elem = item.find('title')
                link_elem = item.find('link')
                
                if title_elem is None or link_elem is None:
                    continue
                
                teks_tweet = title_elem.text.lower()
                link_tweet = link_elem.text.replace('nitter.privacydev.net', 'twitter.com') # Normalisasi link ke domain utama

                # Pencocokan kata kunci cerdas (Keyword Matching)
                for kw in kata_kunci:
                    if kw in teks_tweet:
                        judul = f"🚨 TARGET: '{kw.upper()}' di @{akun}"
                        isi = f"**Peluang Afiliasi Terdeteksi!**\n\n**Konten:** {title_elem.text}\n\n**Tautan Akses:** {link_tweet}\n\n*Segera buka tautan di atas dan balas menggunakan strategi terbaik Anda!*"
                        
                        kirim_notifikasi(judul, isi)
                        break # Hentikan pencocokan keyword ganda pada tweet yang sama

        except Exception as e:
            print(f"⚠️ Terjadi kendala saat memproses @{akun}: {e}")

if __name__ == "__main__":
    mulai_intai_alternatif()
