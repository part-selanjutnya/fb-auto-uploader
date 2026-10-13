import json
import os
import requests
from ntscraper import Nitter

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

# 2. Siapkan Token & Pengintai
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")
scraper = Nitter(log_level=1, skip_instance_check=False)

def kirim_notifikasi(judul, isi):
    url = f"https://api.github.com/repos/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"title": judul, "body": isi}
    res = requests.post(url, headers=headers, json=data)
    if res.status_code == 201:
        print(f"✅ Notifikasi berhasil dikirim: {judul}")
    else:
        print(f"❌ Gagal mengirim notifikasi: {res.text}")

def mulai_intai():
    kata_kunci = [k.lower() for k in config.get("kata_kunci", [])]
    
    for akun in config.get("target_akun", []):
        print(f"🔍 Menyisir @{akun}...")
        try:
            # Mengambil 5 cuitan terbaru dengan pengaman ekstra
            hasil = scraper.get_tweets(akun, mode='user', number=5)
            
            if not hasil or 'tweets' not in hasil or not hasil['tweets']:
                print(f"⚠️ Tidak ada data tweet yang bisa diambil dari @{akun}")
                continue
                
            for tweet in hasil['tweets']:
                if 'text' not in tweet:
                    continue
                    
                teks_tweet = tweet['text'].lower()
                
                # Cek apakah ada kata kunci yang cocok di dalam teks
                for kw in kata_kunci:
                    if kw in teks_tweet:
                        judul = f"🚨 TARGET: '{kw.upper()}' di @{akun}"
                        link = tweet.get('link', 'https://twitter.com')
                        
                        # Format pesan notifikasi
                        isi = f"**Target ditemukan!**\n\n**Teks:** {tweet['text']}\n\n**Buka di Twitter:** {link}\n\n*Segera balas menggunakan foto produk estetik Anda!*"
                        
                        kirim_notifikasi(judul, isi)
                        break 
        except Exception as e:
            print(f"⚠️ Gagal memproses @{akun} (Akan dilewati): {e}")

if __name__ == "__main__":
    if not GITHUB_TOKEN or not REPO_NAME:
        print("⚠️ Dijalankan secara lokal (Bukan di GitHub Actions).")
    mulai_intai()
