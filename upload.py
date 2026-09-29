import os
import json
import subprocess
import requests
import urllib3

# Matikan peringatan SSL Insecure Warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi File & Secret
LINKS_FILE = "links.txt"
FB_PAGES_DATA = os.environ.get("FB_PAGES_DATA")

DEFAULT_CAPTION = """https://part-selanjutnya.github.io/part-selanjutnya/
Tonton selanjutnya☝️
#AlurCeritaFilm #ShortMovie #FilmPendek #CeritaSeru #DramaReels #CuplikanFilm #SinopsisFilm #RekomendasiFilm #FacebookReels #ReelsViral #FYPReels #ReelsIndonesia #VideoViral #TrendingReels"""

def download_video_via_api(url, output_path="temp_video.mp4"):
    print(f"Mengunduh video dari: {url}")
    
    # Resolusi shortlink vt.tiktok.com
    session = requests.Session()
    session.verify = False  # Bypass SSL Certificate verification error
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.tikwm.com/"
    }
    
    try:
        res_head = session.get(url, headers=headers, allow_redirects=True, timeout=15)
        clean_url = res_head.url
    except Exception:
        clean_url = url
    print(f"URL target teresolusi: {clean_url}")

    # Metode 1: TikWM POST API (Form Payload)
    try:
        print("Mengunduh via TikWM POST API (Method 1)...")
        api_url = "https://www.tikwm.com/api/"
        payload = {
            "url": clean_url,
            "count": 12,
            "cursor": 0,
            "web": 1,
            "hd": 1
        }
        res = session.post(api_url, data=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("data", {}).get("play") or data.get("data", {}).get("wmplay")
            if video_url:
                if not video_url.startswith("http"):
                    video_url = f"https://www.tikwm.com{video_url}"
                video_bytes = session.get(video_url, headers=headers, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh video via TikWM!")
                return output_path
    except Exception as e:
        print(f"TikWM Method 1 gagal: {e}")

    # Metode 2: Tiklydown API (Bypass SSL)
    try:
        print("Mengunduh via Tiklydown API (Method 2)...")
        api_url = f"https://api.tiklydown.eu.org/api/download?url={clean_url}"
        res = session.get(api_url, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("video", {}).get("noWatermark") or data.get("video", {}).get("watermark")
            if video_url:
                video_bytes = session.get(video_url, headers=headers, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh video via Tiklydown!")
                return output_path
    except Exception as e:
        print(f"Tiklydown Method 2 gagal: {e}")

    # Metode 3: SSSTik API / Extractor
    try:
        print("Mengunduh via SSSTik API (Method 3)...")
        ssstik_url = "https://ssstik.io/abc?url=dl"
        payload = {
            "id": clean_url,
            "locale": "en",
            "tt": "S3R3Y2E1"
        }
        res = session.post(ssstik_url, data=payload, headers=headers, timeout=20)
        if res.status_code == 200 and "download" in res.text:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            download_link = soup.find("a", {"class": "download_link"})
            if download_link and download_link.get("href"):
                dl_url = download_link["href"]
                video_bytes = session.get(dl_url, headers=headers, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh video via SSSTik!")
                return output_path
    except Exception as e:
        print(f"SSSTik Method 3 gagal: {e}")

    raise Exception("Gagal mengunduh video dari semua metode yang tersedia.")

def upload_to_facebook_page(page_id, page_token, video_path):
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        'description': DEFAULT_CAPTION,
        'access_token': page_token
    }
    with open(video_path, 'rb') as video_file:
        files = {'source': video_file}
        print(f"Mengunggah ke Halaman ID: {page_id}...")
        response = requests.post(url, data=payload, files=files)
        return response.json()

def main():
    if not os.path.exists(LINKS_FILE):
        print(f"Error: File {LINKS_FILE} tidak ditemukan.")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Cari link pertama yang belum diproses (tidak diawali #DONE)
    target_index = -1
    target_url = ""
    for idx, line in enumerate(lines):
        if not line.startswith("#DONE"):
            target_index = idx
            target_url = line
            break

    if target_index == -1 or not target_url:
        print("Semua video di links.txt sudah selesai diposting!")
        return

    if not FB_PAGES_DATA:
        print("Error: Secret FB_PAGES_DATA tidak ditemukan di environment variable.")
        return

    try:
        pages = json.loads(FB_PAGES_DATA)
    except Exception as e:
        print(f"Error: Gagal parse JSON FB_PAGES_DATA: {e}")
        return

    video_file = "temp_video.mp4"

    try:
        # 1. Download video
        download_video_via_api(target_url, video_file)

        # 2. Upload ke seluruh Facebook Pages yang terdaftar
        for page in pages:
            res = upload_to_facebook_page(page['id'], page['token'], video_file)
            print(f"Hasil Upload [{page.get('name', page['id'])}]: {res}")

        # 3. Tandai link dengan #DONE setelah sukses diposting
        lines[target_index] = f"#DONE {target_url}"
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

        print("Proses selesai! Video berhasil diposting dan links.txt diperbarui.")

    except Exception as e:
        print(f"Gagal memproses video: {e}")

    finally:
        # 4. Bersihkan berkas sementara
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    main()
